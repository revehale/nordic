# nordic - Norwegian-English Dictionary Tool

A command-line tool for searching Norwegian words and their English translations.

## Installation

```bash
pip3 install -e .
```

Show help:
```bash
nor --help
```

## Basic Usage

```bash
nordic <search_term>
```

The basic search looks for words that fit search term. For example, `nordic hus` will find "hus". If it finds no results matching your term, it will default to matches that begin with your search time.

## Search Patterns

### Exact Match (default)
```bash
nordic ære
```
Looks for exact matches (including e.g., ære¹, ære², etc.). If no exact matches are found, it defaults to a prefix match.

### Prefix Match
```bash
nordic ære@
```
Add `@` after your search term to explicitly search for words starting with that term. This will find words like 'ære', 'æresdrap', etc.

### Match Anywhere in Term
```bash
nordic @ære
# or
nordic @ære@
```
Add `@` before your search term (wrapping it in @ does the same) to find the term anywhere in main terms. This will match words like 'ære', 'æresdrap', 'lærebok', etc. It will not search definitions or example sentences.

### Full Text Search
```bash
nordic %nasjonal
```
Add `%` before your search term to search through all text, including definitions. This searches both headwords and their definitions.

## Special Search Modes

### English Word Search
```bash
nordic -e|--english <word>
```
Search for English words within the definitions. This helps you find Norwegian words based on their English translations.

### List Words by Category
```bash
nordic -l|--list <category>
```
This will list all words that meet a certain description (NOTE: You may get hundreds or thousands of results).

Available categories:
- `m` - masculine nouns
- `f` - feminine nouns
- `c` - common gender nouns (m/f)
- `n` - neuter nouns
- `w` - nouns without gender identified
- `adj` - adjectives
- `v` - verbs
- `adv` - adverbs
- `u` - unidentified type words

Example: `nordic -l adj` lists all adjectives.

Note: the 'w' and 'u' is to help identify words that may have a gender or a word type, but this application is currently unable to automatically identify it with its search mechanism. 

## Study Tools

### Sample Sentences

```bash
nordic -x|--examples <term>
```

Searches for a word, returning its definition but then also loads any matching sentences in the Tatoeba sentence list for Norwegian.

Example: `nordic -x hus` returns the definition and sample sentences from Tatoeba with 'hus' in it.

### Random Words with Definitions

```bash
nordic -r[N]|--random[N]
```
Get N random words from the dictionary. If N is not specified, returns 1 word.

Example: `nordic -r5` returns 5 random words and their definitions.

### Random Words

```bash
nordic -R[N]
```

Get N random words from the dictionary. If N is not specified, returns 1 word (set in config file). Only returns the words themselves, no definitions.

Example: `nordic -R5` returns 5 random words.

### Flashcard Mode
```bash
nordic -f[N]|--flash[N]
```
Start an interactive flashcard session with N random words (default: 10, set in config file).
- Shows Norwegian word first
- Press any key to reveal definition
- SPACE to mark as remembered
- BACKSPACE/DELETE to keep reviewing
- Ctrl+C to exit

Example: `nordic -f20` starts a flashcard session with 20 words.

### Quiz Mode
```bash
nordic -q[N]|--quiz[N]
```
Start an interactive multiple-choice quiz with N random words (default: 10, set in config file).
- Shows Norwegian word
- Presents multiple choice options for the definition
- Tracks your correct/incorrect answers
- Continues until all words are learned

## Utility Commands

### Statistics
```bash
nordic -s|--stats
```
Display detailed statistics about the dictionary, including:
- Total number of entries
- Word type distributions
- Gender distributions for nouns
- Letter frequency statistics

### Test Searches
```bash
nordic -t|--test <search term>
```
Run a series of predefined test searches to demonstrate the different search patterns to make sure the dictionary is working. No need to add a search term for this.

If you add a search term it will search for just that word but will return it as raw markdown for debugging of the raw dictionary data.

## Configuration

## Configuration

The dictionary tool can be configured using a YAML configuration file located at `~/.config/nordic/config.yaml`. You can edit this file directly or use the configuration wizard:

```
nordic -c|--config
```

The configuration wizard will walk you through setting up each option interactively.

### Configuration Options

#### Colors

- `headword`: Color for headword highlighting (default: light_green)
- `grammar`: Color for grammar annotations (default: yellow)
- `match`: Color for matched text in wildcard searches (default: grey)
- `highlight_background`: Color for the background of highlighted matches (default: yellow)

Available colors include: grey, red, green, yellow, blue, magenta, cyan, white, and their light/dark variants (e.g., light_blue, dark_grey).

#### Study Tool Defaults

- `quiz_word_count`: Default number of words for quiz mode (default: 10)
- `flashcard_count`: Default number of words for flashcard mode (default: 10)
- `random_word_count`: Default number of words for random word retrieval with -r (default: 1)
- `random_headword_count`: Default number of words for random headword retrieval with -R (default: 1)

#### Behavior Settings

- `fallback_to_prefix`: If true, falls back to prefix search when no exact match is found (default: true)
- `silent_fail`: If true, suppresses "no entry found" messages (default: false)

### Example Configuration

```
colors:
  headword: light_green
  grammar: yellow
  match: grey
  highlight_background: yellow
flashcard_count: 10
quiz_word_count: 10
random_word_count: 1
random_headword_count: 1
fallback_to_prefix: true
silent_fail: false
```

You can modify these settings either by editing the config file directly or using the configuration wizard with `nordic -c`.

## Usage Examples

```bash
nordic hus              # Find the word "hus" and words starting with "hus"
nordic @hus             # Find "hus" anywhere in words
nordic %hus             # Search for "hus" in words and definitions
nordic -e house         # Find Norwegian words containing "house" in their definitions
nordic -l v            # List verbs
nordic -r5             # Get 5 random words
nordic -f15            # Start flashcards with 15 words
nordic -q20            # Start a quiz with 20 words
```
