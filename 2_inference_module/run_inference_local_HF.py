"""Local inference with Hugging Face `transformers` (GPU, e.g. Google Colab).

Alternative to run_inference_LangChain_HF.py, which needs the paid/limited remote Hugging
Face endpoint. This script loads the model on the local GPU instead, so it needs no
inference API. It also stores the log-probability of every generated token, which the
uncertainty part of the project needs (a remote endpoint does not give them).

Output: same file names and format as the original script, a list of
    {"index", "prompt", "generated_text", "token_ids", "token_logprobs"}
so 2_inference_module/post_process_generated_string.py accepts it unchanged
(the extra keys are just carried along).

`token_logprobs[i]` is log P(token_i | previous tokens) under the model's own
distribution (before temperature), so it measures the model's confidence in the token it
produced, not the effect of the sampling temperature.

Prompts are sent as raw text, as in the original script (no chat template).
Generation settings are the original ones: max_new_tokens=512, temperature=0.5, sampling.

Run from the repository root, for example:
    python 2_inference_module/run_inference_local_HF.py --limit 3 --out_dir out_teste
    python 2_inference_module/run_inference_local_HF.py --out_dir out_llama_local
"""
import argparse
import json
import logging
import os
import sys
import time

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer


def read_prompts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)


def load_model(name, quantize):
    kwargs = {}
    if torch.cuda.is_available():
        if quantize:
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
        else:
            kwargs["torch_dtype"] = torch.float16
        kwargs["device_map"] = "auto"
    else:
        logging.warning("No GPU found: running on CPU, this will be very slow.")
    tokenizer = AutoTokenizer.from_pretrained(name, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(name, **kwargs)
    model.eval()
    return tokenizer, model


def stop_token_ids(tokenizer):
    """EOS plus Llama-3's <|eot_id|> when it exists."""
    ids = {tokenizer.eos_token_id}
    eot = tokenizer.convert_tokens_to_ids("<|eot_id|>")
    if isinstance(eot, int) and eot != tokenizer.unk_token_id and eot >= 0:
        ids.add(eot)
    return [i for i in ids if i is not None]


@torch.no_grad()
def generate_batch(tokenizer, model, prompts, max_new_tokens, temperature, stops):
    enc = tokenizer(prompts, return_tensors="pt", padding=True).to(model.device)
    out = model.generate(
        **enc,
        max_new_tokens=max_new_tokens,
        do_sample=temperature > 0,
        temperature=temperature if temperature > 0 else None,
        top_p=1.0,
        top_k=0,
        eos_token_id=stops,
        pad_token_id=tokenizer.pad_token_id,
        return_dict_in_generate=True,
        output_logits=True,  # raw logits, before temperature
    )
    prompt_len = enc["input_ids"].shape[1]
    new_ids = out.sequences[:, prompt_len:]
    # log P(chosen token) under the untempered distribution
    logprobs = model.compute_transition_scores(out.sequences, out.logits, normalize_logits=True)

    results = []
    for row in range(new_ids.shape[0]):
        ids = new_ids[row].tolist()
        lps = logprobs[row].float().tolist()
        end = len(ids)
        for pos, tid in enumerate(ids):  # cut after the first stop token
            if tid in stops:
                end = pos
                break
        ids, lps = ids[:end], lps[:end]
        text = tokenizer.decode(ids, skip_special_tokens=True)
        results.append((text, ids, lps))
    return results


def main():
    logging.basicConfig(level=logging.INFO)
    start = time.time()

    p = argparse.ArgumentParser()
    p.add_argument("--input_folder", default="1_data_module/2_creating_prompts/data_with_prompts",
                   help="Folder with the prompt files (run from the repository root)")
    p.add_argument("--model_name", default="meta-llama/Meta-Llama-3-8B-Instruct",
                   help="Hugging Face model id or local folder")
    p.add_argument("--out_dir", default="generated_local", help="Output directory")
    p.add_argument("--only", default="three_shot_RAG",
                   help="Run only prompt files whose name starts with this text. '' = all 17")
    p.add_argument("--limit", type=int, default=0, help="Only the first N prompts of each file (0 = all)")
    p.add_argument("--batch_size", type=int, default=4, help="Prompts per generate() call")
    p.add_argument("--max_new_tokens", type=int, default=512)
    p.add_argument("--temperature", type=float, default=0.5)
    p.add_argument("--no_4bit", action="store_true",
                   help="Load in fp16 instead of 4-bit (an 8B model needs ~16 GB, too much for a free T4)")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    if not os.path.isdir(args.input_folder):
        sys.exit(f"The folder '{args.input_folder}' does not exist. Run from the repository root "
                 f"or pass --input_folder.")
    file_names = sorted(f for f in os.listdir(args.input_folder)
                        if f.endswith(".json") and f.startswith(args.only))
    if not file_names:
        sys.exit(f"No prompt file in '{args.input_folder}' starts with '{args.only}'.")
    logging.info("Files to run: %s", file_names)
    os.makedirs(args.out_dir, exist_ok=True)

    torch.manual_seed(args.seed)
    tokenizer, model = load_model(args.model_name, quantize=not args.no_4bit)
    stops = stop_token_ids(tokenizer)

    for name in file_names:
        prompts = read_prompts(os.path.join(args.input_folder, name))
        if args.limit:
            prompts = prompts[:args.limit]
        out_path = os.path.join(args.out_dir, name)

        results = []
        done = 0
        if os.path.exists(out_path):  # resume after a Colab disconnect
            with open(out_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            done = len(results)
            logging.info("Resuming %s from prompt %d", name, done)

        # Process in length order inside each chunk of 8 batches to waste less padding,
        # but keep the saved list in the original order.
        todo = list(range(done, len(prompts)))
        bar = tqdm(total=len(prompts), initial=done, desc=f"{args.model_name} on {name}")
        chunk = args.batch_size * 8
        for c in range(0, len(todo), chunk):
            idxs = todo[c:c + chunk]
            order = sorted(idxs, key=lambda i: len(prompts[i]))
            by_index = {}
            for b in range(0, len(order), args.batch_size):
                batch_idx = order[b:b + args.batch_size]
                outs = generate_batch(tokenizer, model, [prompts[i] for i in batch_idx],
                                      args.max_new_tokens, args.temperature, stops)
                for i, (text, ids, lps) in zip(batch_idx, outs):
                    by_index[i] = {"index": i, "prompt": prompts[i], "generated_text": text,
                                   "token_ids": ids, "token_logprobs": lps}
                bar.update(len(batch_idx))
            results.extend(by_index[i] for i in idxs)
            save(out_path, results)  # progress saved after every chunk
        bar.close()
        save(out_path, results)
        logging.info("Saved %s", out_path)

    print(f"Elapsed time: {(time.time() - start) / 60:.2f} minutes")


if __name__ == "__main__":
    main()
