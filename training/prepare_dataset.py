"""
Baixa o dataset de fire/smoke do Hugging Face e organiza em splits YOLO.

Classes mapeadas para o FireWatch:
  0 = foco_ativo  (fire no dataset original)
  1 = fumaca      (smoke no dataset original)
  2 = area_queimada (sem exemplos neste dataset — adicionado na Fase 2.2)

Uso:
  python prepare_dataset.py
"""
import os
import shutil
import random
from pathlib import Path

HF_DATASET = "Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset"
HF_PREFIX  = "CCTV_Fire_Smoke_Emergency_Detection_Dataset"
DEST       = Path(__file__).parent / "datasets" / "firewatch"

TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
# restante vai para test

def main():
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    files = list(api.list_repo_files(HF_DATASET, repo_type="dataset"))

    img_files = sorted(f for f in files if f.startswith(f"{HF_PREFIX}/images/"))
    lbl_files = {
        Path(f).stem: f
        for f in files
        if f.startswith(f"{HF_PREFIX}/labels/") and f.endswith(".txt")
    }

    print(f"Encontradas {len(img_files)} imagens e {len(lbl_files)} labels")

    # Filtra apenas imagens que têm label correspondente
    paired = [(f, lbl_files[Path(f).stem]) for f in img_files if Path(f).stem in lbl_files]
    print(f"Pares imagem+label: {len(paired)}")

    random.seed(42)
    random.shuffle(paired)

    n_train = int(len(paired) * TRAIN_RATIO)
    n_val   = int(len(paired) * VAL_RATIO)
    splits = {
        "train": paired[:n_train],
        "val":   paired[n_train:n_train + n_val],
        "test":  paired[n_train + n_val:],
    }

    for split, pairs in splits.items():
        print(f"  {split}: {len(pairs)} pares")

    # Limpa e recria diretórios
    for split in ["train", "val", "test"]:
        for kind in ["images", "labels"]:
            d = DEST / kind / split
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)

    # Download e copia dos arquivos
    total = sum(len(v) for v in splits.values())
    done = 0
    for split, pairs in splits.items():
        for img_hf, lbl_hf in pairs:
            stem = Path(img_hf).stem
            ext  = Path(img_hf).suffix

            img_local = hf_hub_download(HF_DATASET, img_hf, repo_type="dataset")
            lbl_local = hf_hub_download(HF_DATASET, lbl_hf, repo_type="dataset")

            shutil.copy(img_local, DEST / "images" / split / f"{stem}{ext}")
            shutil.copy(lbl_local, DEST / "labels" / split / f"{stem}.txt")

            done += 1
            print(f"\r  [{done}/{total}] {split}/{stem}{ext}", end="", flush=True)

    print(f"\n\nDataset pronto em: {DEST}")

    # Gera o data.yaml final
    yaml_path = Path(__file__).parent / "data.yaml"
    yaml_path.write_text(
        f"path: {DEST.resolve()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n\n"
        "nc: 3\n"
        "names:\n"
        "  0: foco_ativo\n"
        "  1: fumaca\n"
        "  2: area_queimada\n"
    )
    print(f"data.yaml atualizado: {yaml_path}")


if __name__ == "__main__":
    main()
