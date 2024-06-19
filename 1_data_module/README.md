Data Module
==========================

The Data Module contains two sub-modules:

1. Data Preprocessing
----------------------
Downloading RED-fm and shaping it according to our needs.

A data instance from the test set before preprocessing:

```{
    "docid": "1755878-0",
    "title": "Porsche Panamera",
    "uri": "Q501349",
    "text": "The Porsche Panamera is a mid/full-sized luxury vehicle (E-segment in Europe) manufactured by the German automobile manufacturer Porsche. It is front-engined and has a rear-wheel-drive layout, with all-wheel drive versions also available.",
    "entities": [
        {
            "uri": "Q501349",
            "surfaceform": "Porsche Panamera",
            "type": "MISC",
            "start": 4,
            "end": 20
        },
        {
            "uri": "Q5581707",
            "surfaceform": "luxury vehicle",
            "type": "Concept",
            "start": 41,
            "end": 55
        },
        {
            "uri": "Q17105090",
            "surfaceform": "E-segment",
            "type": "MISC",
            "start": 57,
            "end": 66
        },
        {
            "uri": "Q46",
            "surfaceform": "Europe",
            "type": "LOC",
            "start": 70,
            "end": 76
        },
        {
            "uri": "Q183",
            "surfaceform": "German",
            "type": "LOC",
            "start": 98,
            "end": 104
        },
        {
            "uri": "Q40993",
            "surfaceform": "Porsche",
            "type": "LOC",
            "start": 129,
            "end": 136
        },
        {
            "uri": "Q9460131",
            "surfaceform": "front-engined",
            "type": "UNK",
            "start": 144,
            "end": 157
        },
        {
            "uri": "Q1070558",
            "surfaceform": "rear-wheel-drive",
            "type": "Concept",
            "start": 168,
            "end": 184
        },
        {
            "uri": "Q12211810",
            "surfaceform": "all-wheel drive",
            "type": "UNK",
            "start": 198,
            "end": 213
        }
    ],
    "relations": [
        {
            "subject": {
                "uri": "Q501349",
                "surfaceform": "Porsche Panamera",
                "type": "MISC",
                "start": 4,
                "end": 20
            },
            "predicate": 19,
            "object": {
                "uri": "Q40993",
                "surfaceform": "Porsche",
                "type": "LOC",
                "start": 129,
                "end": 136
            }
        },
        {
            "subject": {
                "uri": "Q40993",
                "surfaceform": "Porsche",
                "type": "LOC",
                "start": 129,
                "end": 136
            },
            "predicate": 0,
            "object": {
                "uri": "Q183",
                "surfaceform": "German",
                "type": "LOC",
                "start": 98,
                "end": 104
            }
        }
    ]
}
```

Run `1_data_module/1_data_preprocessing/convert_REDFM.py`

The same data instance after preprocessing:

```
{
    "Text": "The Porsche Panamera is a mid/full-sized luxury vehicle (E-segment in Europe) manufactured by the German automobile manufacturer Porsche. It is front-engined and has a rear-wheel-drive layout, with all-wheel drive versions also available.",
    "Entities": [
        "Porsche Panamera",
        "luxury vehicle",
        "E-segment",
        "Europe",
        "German",
        "Porsche",
        "front-engined",
        "rear-wheel-drive",
        "all-wheel drive"
    ],
    "Entity Types": [
        "Luxury vehicle is a/an concept.",
        "Front-engined is a/an unknown.",
        "Rear-wheel-drive is a/an concept.",
        "All-wheel drive is a/an unknown."
    ],
    "Entity wiki ids": [
        "Luxury vehicle has a Wikidata ID of Q5581707.",
        "Front-engined has a Wikidata ID of Q9460131.",
        "Rear-wheel-drive has a Wikidata ID of Q1070558.",
        "All-wheel drive has a Wikidata ID of Q12211810."
    ],
    "Relations": [
        "manufacturer",
        "country"
    ],
    "Relation wiki ids": [
        "Manufacturer has the Wikidata ID of P176.",
        "Country has the Wikidata ID of P17."
    ],
    "Triples": [
        [
            "Porsche Panamera",
            "Manufacturer",
            "Porsche"
        ],
        [
            "Porsche",
            "Country",
            "German"
        ]
    ],
    "Wiki Triples": [
        [
            "Q501349",
            "P176",
            "Q40993"
        ],
        [
            "Q40993",
            "P17",
            "Q183"
        ]
    ],
    "Mixed Triples": [
        [
            "Porsche",
            "country",
            "luxury vehicle"
        ],
        [
            "Porsche",
            "Country",
            "German"
        ],
        [
            "luxury vehicle",
            "manufacturer",
            "rear-wheel-drive"
        ],
        [
            "Porsche Panamera",
            "Manufacturer",
            "Porsche"
        ]
    ],
    "Corrupted Triples": [
        [
            "luxury vehicle",
            "manufacturer",
            "rear-wheel-drive"
        ],
        [
            "Porsche",
            "country",
            "luxury vehicle"
        ]
    ],
    "Explanations": [
        "The relation - manufacturer - does not hold between luxury vehicle and rear-wheel-drive.",
        "The relation - country - does not hold between Porsche and luxury vehicle."
    ]
}
```

2. Creating Prompts
--------------------
Prompting strategies employed:
- Simple instruction
- Chain of thought
- Chain of thought with self-consistency
- Generated Knowledge
- Reason and Act

Adding examples (task demonstrations) to selected prompt templates:
- Canonical example
- One canonical example
- Three canonical examples
- Similarity-based example selection mechanism
- One selected example
- Three selected examples

Five prompting strategies combined with different example incorporation choices result in 17 different prompts.

**Simple instruction:**
- No task demonstration (zero-shot)
- 1 canonical task demonstration (one-shot)
- 3 canonical task demonstrations (few-shot)
- 1 task demonstration retrieved from the training corpus based on the maximum marginal relevance metric
- 3 task demonstrations retrieved from the training corpus based on the maximum marginal relevance metric

**Chain of thought:**
- No task demonstration (zero-shot)
- 1 task demonstration retrieved from the training corpus based on the maximum marginal relevance metric (RAG one-shot)
- 3 task demonstrations retrieved from the training corpus based on the maximum marginal relevance metric (RAG three-shot)

**Chain of thought with self-consistency:**
- No task demonstration (zero-shot)
- 1 task demonstration retrieved from the training corpus based on the maximum marginal relevance metric (one-shot)
- 3 task demonstrations retrieved from the training corpus based on the maximum marginal relevance metric (few-shot)

**Generated Knowledge:**
- No task demonstration (zero-shot)
- 1 task demonstration retrieved from the training corpus based on the maximum marginal relevance metric (one-shot)
- 3 task demonstrations retrieved from the training corpus based on the maximum marginal relevance metric (few-shot)

**Reason and Act:**
- No task demonstration (zero-shot)
- 1 task demonstration retrieved from the training corpus based on the maximum marginal relevance metric (one-shot)
- 3 task demonstrations retrieved from the training corpus based on the maximum marginal relevance metric (few-shot)

Prompt templates can be created manually or using `1_data_module/2_creating_prompts/template_creator.py`

To place the data into our prompt templates, there are two options:

**No Retrieval Prompt Compiler:**
Run 

`1_data_module/2_creating_prompts/no_retrieval_prompt_compiler.py`

This script works with no demonstration (zero-shot) and fixed canonical task demonstration (example) setting. It places data variables into assigned placeholder areas.

**Retrieval Augmented Prompt Compiler:**
Run 

`1_data_module/2_creating_prompts/retrieval_augmented_prompt_compiler.py`

This script dynamically selects task demonstrations using the "maximum marginal relevance" example selector among example vectors embedded by InstructorEmbeddings.

Resulting prompts can be found in `1_data_module/2_creating_prompts/data_with_prompts`. This is the input folder for the inference module.
