"""Inference with a local Ollama model through LangChain, saving token log-probabilities.

Based on run_inference_LangChain_HF.py (Luis' Ollama version). Same model call
(ChatOllama, temperature=0, reasoning=False); differences:
  - asks Ollama for log-probabilities (logprobs=True, optional top_logprobs) and saves them;
  - --only selects the prompt files (default: the zero-shot baseline);
  - --limit runs only the first N prompts of each file (default: 100);
  - progress is saved every 25 prompts and a rerun resumes from the saved file;
  - failed calls are retried; no dependency on the `retry` package.

Output: same file names and format as the original script, a list of
    {"index", "prompt", "generated_text", "logprobs"}
where "logprobs" is a list with one entry per generated token:
    {"token", "logprob", "top_logprobs": [{"token", "logprob"}, ...]}   (top_logprobs only if requested)
2_inference_module/post_process_generated_string.py accepts it unchanged (extra keys are carried along).

Run from the repository root, for example:
    python 2_inference_module/run_inference_ollama_logprobs.py --model_name qwen3.5:4b --limit 3 --out_dir out_teste
    python 2_inference_module/run_inference_ollama_logprobs.py --model_name qwen3.5:4b --out_dir out_zero_shot_100
"""
import argparse
import json
import logging
import os
import sys
import time

from langchain_ollama import ChatOllama
from tqdm import tqdm


def read_prompts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)


def clean_logprobs(raw):
    """Keep token, logprob and top_logprobs; drop the raw bytes to keep files small."""
    if not raw:
        return None
    out = []
    for entry in raw:
        item = {"token": entry.get("token"), "logprob": entry.get("logprob")}
        if entry.get("top_logprobs"):
            item["top_logprobs"] = [{"token": t.get("token"), "logprob": t.get("logprob")}
                                    for t in entry["top_logprobs"]]
        out.append(item)
    return out


def invoke_with_retry(llm, prompt, tries=3, delay=5):
    for attempt in range(1, tries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as exc:
            if attempt == tries:
                raise
            logging.warning("Call failed (%s). Retry %d/%d in %ds", exc, attempt, tries - 1, delay * attempt)
            time.sleep(delay * attempt)


def main():
    logging.basicConfig(level=logging.INFO)
    start = time.time()

    p = argparse.ArgumentParser()
    p.add_argument("--input_folder", default="1_data_module/2_creating_prompts/data_with_prompts",
                   help="Folder with the prompt files (run from the repository root)")
    p.add_argument("--model_name", default="qwen3.5:4b", help="Ollama model name")
    p.add_argument("--out_dir", default="generated_ollama_logprobs", help="Output directory")
    p.add_argument("--only", default="zero_shot_prompts",
                   help="Run only prompt files whose name starts with this text ('' = all 17)")
    p.add_argument("--limit", type=int, default=100,
                   help="Run only the first N prompts of each file (0 = all 446)")
    p.add_argument("--top_logprobs", type=int, default=5,
                   help="Alternatives saved per token (0 = only the chosen token)")
    p.add_argument("--no_logprobs", action="store_true", help="Do not request log-probabilities")
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

    kwargs = dict(model=args.model_name, temperature=0, reasoning=False)
    if not args.no_logprobs:
        kwargs["logprobs"] = True
        if args.top_logprobs > 0:
            kwargs["top_logprobs"] = args.top_logprobs
    llm = ChatOllama(**kwargs)

    for name in file_names:
        prompts = read_prompts(os.path.join(args.input_folder, name))
        if args.limit:
            prompts = prompts[:args.limit]
        out_path = os.path.join(args.out_dir, name)

        results = []
        if os.path.exists(out_path):  # resume after a disconnect
            with open(out_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            logging.info("Resuming %s from prompt %d", name, len(results))

        for i in tqdm(range(len(results), len(prompts)), initial=len(results), total=len(prompts),
                      desc=f"{args.model_name} on {name}"):
            msg = invoke_with_retry(llm, prompts[i])
            entry = {"index": i, "prompt": prompts[i], "generated_text": msg.content}
            if not args.no_logprobs:
                entry["logprobs"] = clean_logprobs((msg.response_metadata or {}).get("logprobs"))
            results.append(entry)
            if (i + 1) % 25 == 0:
                save(out_path, results)
        save(out_path, results)
        logging.info("Saved %s", out_path)

        if not args.no_logprobs and results and not results[0].get("logprobs"):
            logging.warning("The model returned NO log-probabilities. Check the Ollama and "
                            "langchain-ollama versions (pip install -U langchain-ollama).")

    print(f"Elapsed time: {(time.time() - start) / 60:.2f} minutes")


if __name__ == "__main__":
    main()
