import pytest
from prompt_service import get_categories, get_prompts_by_category, get_random_prompt, load_prompts

def test_load_prompts_returns_list():
    prompts = load_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) > 0

def test_get_categories():
    categories = get_categories()
    assert isinstance(categories, list)
    # Expect at least 6 categories based on markdown
    assert len(categories) >= 6

def test_prompts_by_category():
    categories = get_categories()
    cat = categories[0]
    prompts = get_prompts_by_category(cat)
    assert isinstance(prompts, list)
    assert len(prompts) > 0

def test_random_prompt():
    prompt = get_random_prompt()
    assert isinstance(prompt, str)
    # Ensure it's one of the prompts
    all_prompts = [p['prompt'] for p in load_prompts()]
    assert prompt in all_prompts

def test_random_prompt_with_category():
    cat = get_categories()[0]
    prompt = get_random_prompt(cat)
    assert isinstance(prompt, str)
    # Ensure belongs to category
    cat_prompts = get_prompts_by_category(cat)
    assert prompt in cat_prompts
