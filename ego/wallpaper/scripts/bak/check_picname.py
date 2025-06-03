from pathlib import Path

if __name__ == "__main__":
    pics_dir = Path(__file__).resolve().parent / "pics"

    print(pics_dir)

    pics_list = []
    for jpg in pics_dir.glob("**/*.jpg"):
        pics_list.append(jpg.name)

    print(len(pics_list))
    print(len(set(pics_list)))
