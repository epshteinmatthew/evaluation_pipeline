import json
import os
import string

import ollama, re, extractcontent

with open("paper.txt", "r") as fp:
    text = fp.read()

# Extract images and text from PDFs
extractor = extractcontent.PDFExtractor("paper")
extractor.extract_images_and_text()



# Process Markdown files
markdown_processor = extractcontent.MarkdownProcessor("paper")
for subfolder in os.listdir(markdown_processor.directory):
    subfolder_path = os.path.join(markdown_processor.directory, subfolder)
    if os.path.isdir(subfolder_path):
        print(f"Found directory: {subfolder_path}")

        for file_name in os.listdir(subfolder_path):
            if file_name.endswith('.md'):
                file_path = os.path.join(subfolder_path, file_name)
                print(f"Found Markdown file: {file_path}")
organized_sections = []
sections = markdown_processor.split_markdown_file(file_path)
organized_sections = markdown_processor.organize_sections(sections)


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
                         'of the relevant paper section. Do you understand? (yes/no) '}]

scores = []

evalcriteria = [
    "Ensure the summary is clear, specific, and informative without including unnecessary details.",
    "Ensure the summary captures the rationale behind the research and its potential impact or contribution to the field, presented as a clean and concise background and significance section."
    "Ensure the summary captures the key steps, methodologies, and any relevant parameters or controls, presented as a clear and concise methods section.",
    "Ensure that the summary is concise and accurately reflects the main results and their implications.",
    "Ensure the summary is concise and captures the essence of the authors' conclusions."
]

papersections = [
    organized_sections['summary'],
    organized_sections['background_significance'],
    organized_sections['methods'],
    organized_sections['results'],
    organized_sections['discussion'],
]

for i in range(0,len(summarysplit)-1):
    kmessages.append({'role': 'user',
                      'content': 'This part of the summary is as follows: ' + summarysplit[i] + ". please give it a grade from -10 "
                                                                                  "to 10 based on accuracy and "
                                                                                  "completeness. Don't be afraid to grade honestly. respond ONLY in the "
                                                                                  "following format: [part title (AS "
                                                                                  "GIVEN IN THE TEXT)] : [score]. "
                                                                                  "part title should be enclosed in "
                                                                                  "double quotes!!! do not include "
                                                                                  "any additional commentary!!! make "
                                                                                  "sure that you have summary, "
                                                                                  "background and significance, "
                                                                                  "methods, results, and discussion "
                                                                                  "section. don't leave anything out! "
                                                                                  "dont include more than one new "
                                                                                  "line after each section's score!"
                                                                                   "the relevant section of the paper is as follows" + papersections[i] + ". "  + evalcriteria[i]})
response = ollama.chat(
    model='llama3.1',
    messages=kmessages,
    stream=False,
    options={"temperature" : 0.1}
)

raw = response['message']['content']

re.sub(r'(\D)\1+', r'\1', raw)

print(raw)

formatted = "{" + response['message']['content'].replace("\n", ",") + "}"

responseJSON = json.loads(formatted)


def hallucinated():
    hallucinated = 0

    # Extract title and author
    title1 = '\n'.join(sections[:5])
    author = '\n'.join(sections[1:4])

    # basic search for authors and title
    for part in authors:
        hallucwordscore = 0
        for word in part.split(" "):
            if word not in author:
                hallucwordscore += 1
        if hallucwordscore > len(part.split(" ")) / 2:
            hallucinated+=1
    halluctitlescore = 0
    for word in title.split(" "):
        if word not in title1:
            halluctitlescore += 1
    if halluctitlescore > len(title.split(" ")) / 2:
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

    return hallucinated



def eval(abstract_score, background_score, methods_score, results_score, discussion_score):
    score = (abstract_score*1.25 + background_score + methods_score*1.5 + results_score*2 + discussion_score*2 - (
                hallucinated() / 5)) * (10/77.5)
    print(score)
    return score > 7.5


print(eval(responseJSON["Overview"], responseJSON["Background and Significance"], responseJSON["Methods"],
           responseJSON["Results"], responseJSON["Discussion"]))
