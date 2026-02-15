import json
import random
import pathlib

# Path to the JSON file containing prompts. It is located in the same directory as this module.
_PROMPT_FILE = pathlib.Path(__file__).with_name('writing_prompts.json')

def _load_prompts():
    """Load the prompts JSON file."""
    return json.loads(_PROMPT_FILE.read_text())



def load_prompts():
    """Public function to load prompts JSON file."""
    return _load_prompts()



def get_categories():
    """Return a sorted list of unique prompt categories."""
    prompts = _load_prompts()
    return sorted({p['category'] for p in prompts})


def get_prompts_by_category(category: str):
    """Return a list of prompts belonging to the given category.

    Args:
        category: The category name.
    """
    prompts = _load_prompts()
    return [p['prompt'] for p in prompts if p['category'] == category]


def get_random_prompt(category: str | None = None) -> str:
    """Return a random prompt.

    If ``category`` is provided, the prompt is chosen from that category only.
    """
    prompts = _load_prompts()
    if category:
        prompts = [p for p in prompts if p['category'] == category]
    if not prompts:
        raise ValueError('No prompts found for the specified category')
    return random.choice(prompts)['prompt']
