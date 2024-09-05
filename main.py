import json
import string

import ollama, re

with open("paper.txt", "r") as p:
    text = p.read()

with open("paper_summary.txt", "r") as z:
    summary = z.read()
    #split into sections
    title = summary.split("#")[1]
    authors = [word for sentence in summary.split("#")[2].split('\n')[1:-2] for word in sentence.split(",", 1)]
    summarysplit = summary.split("#")[3:8]

    #needs work. references are summarized so we need to find out how to do search properly here
    references = summary.split("#")[8].split("\n")[1:]

kmessages = [{'role': 'user',
              'content': 'You are an examiner for summaries of scientific papers. The summaries shall be presented to '
                         'you in parts, with accompanying headings, covering a section of the paper. Your task shall '
                         'be to grade the summary parts on a scale of 0 to 10, based on their accuracy and coverage '
                         'of the relevant paper section. You will also be given the summary as a whole, and your task '
                         'here shall be to count how many important details from the paper are missing from the '
                         'summary. The paper itself is as follows: ' + text + ". Do you understand? (yes/no)"}]

scores = []
for i in summarysplit:
    kmessages.append({'role': 'user',
                      'content': 'This part of the summary is as follows: ' + i + ". please give it a grade from -10 "
                                                                                  "to 10 based on accuracy and "
                                                                                  "completeness. Don't be afraid to grade honestly. respond ONLY in the "
                                                                                  "following format: [part title (AS "
                                                                                  "GIVEN IN THE TEXT)] : [score]. "
                                                                                  "part title should be enclosed in "
                                                                                  "double quotes!!! do not include "
                                                                                  "any additional commentary!!! make "
                                                                                  "sure that you have overview, "
                                                                                  "background and significance, "
                                                                                  "methods, results, and discussion "
                                                                                  "section. don't leave anything out! "
                                                                                  "dont include more than one new "
                                                                                  "line after each section's score!"})
response = ollama.chat(
    model='llama3.1',
    messages=kmessages,
    stream=False
)

raw = response['message']['content']

re.sub(r'(\D)\1+', r'\1', raw)

formatted = "{" + response['message']['content'].replace("\n", ",") + "}"

responseJSON = json.loads(formatted)


def eval(abstract_score, background_score, methods_score, results_score, discussion_score):
    hallucinated = 0

    #basic search for authors and title
    for part in authors:
        if part not in text:
            hallucinated += 1
    if title not in text:
        hallucinated += 1

    #specific words
    results = summary
    translator = str.maketrans('', '', r"""!"#$%&'()*+,./:;<=>?@[\]^_`{|}~""")
    results = results.translate(translator).split(' ')
    # now how do I generate a score?
    maxes = []
    while len(maxes) < 5:
        mostUsed = max(set(results), key=results.count)
        results = [i for i in results if i != mostUsed]
        if mostUsed in ["the", "by", "of", "and", "in", "with", "to", "from", "for", "is", "an", ''] or (
                len(mostUsed) < 5 and mostUsed.isalpha()):
            continue
        maxes.append(mostUsed)
    for item in maxes:
        if item not in text:
            print(item)
            hallucinated += summary.count(item)

    score = (abstract_score*1.25 + background_score + methods_score*1.5 + results_score*2 + discussion_score*2 - (
                hallucinated / 5)) * (10/77.5)
    print(score)
    return score > 7.5


print(eval(responseJSON["Overview"], responseJSON["Background and Significance"], responseJSON["Methods"],
           responseJSON["Results"], responseJSON["Discussion"]))
