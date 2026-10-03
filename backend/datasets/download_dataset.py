import kagglehub

path = kagglehub.dataset_download(
    "dipeshlohchab/arxiv-research-papers"
)

print("Dataset tersimpan di:")
print(path)