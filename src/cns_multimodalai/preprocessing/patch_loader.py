from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

PATCH_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}

def list_patch_images(patch_dir):
    patch_dir = Path(patch_dir)
    paths = []
    for p in patch_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in PATCH_EXTS:
            if "sample_grids" in str(p).lower() or "grid" in p.name.lower():
                continue
            paths.append(p)
    return sorted(paths)

class PatchImageDataset(Dataset):
    def __init__(self, patch_paths, size=224):
        self.patch_paths = [str(p) for p in patch_paths]
        self.tfm = transforms.Compose([
            transforms.Resize((size, size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.patch_paths)

    def __getitem__(self, idx):
        img = Image.open(self.patch_paths[idx]).convert("RGB")
        return self.tfm(img), self.patch_paths[idx]
