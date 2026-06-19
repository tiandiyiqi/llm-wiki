"""Imports OKF bundle into knowledge base."""

import json
import tarfile
from pathlib import Path
from typing import Dict, List, Optional


class OKFImporter:
    """Imports OKF bundle into knowledge base."""

    def __init__(self, bundle_path: Path, output_dir: Path):
        self.bundle_path = bundle_path
        self.output_dir = output_dir
        self.manifest: Optional[Dict] = None
        self.imported_files: List[str] = []

    def import_bundle(self, overwrite: bool = False) -> bool:
        print(f"📦 Importing OKF bundle: {self.bundle_path}")

        if not self.bundle_path.exists():
            print(f"❌ Error: Bundle not found: {self.bundle_path}")
            return False

        if not tarfile.is_tarfile(self.bundle_path):
            print(f"❌ Error: Not a valid tar file: {self.bundle_path}")
            return False

        if self.output_dir.exists() and not overwrite:
            if any(self.output_dir.iterdir()):
                print(f"❌ Error: Output directory not empty: {self.output_dir}")
                print("   Use --overwrite to replace existing content")
                return False

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Extracting to: {self.output_dir}")
        with tarfile.open(self.bundle_path, 'r:gz') as tar:
            try:
                manifest_member = tar.getmember('manifest.json')
                manifest_file = tar.extractfile(manifest_member)
                if manifest_file:
                    self.manifest = json.load(manifest_file)
            except KeyError:
                print("⚠️  Warning: No manifest.json in bundle")
                self.manifest = None

            for member in tar.getmembers():
                if member.name == 'manifest.json':
                    continue
                if member.name.startswith('/') or '..' in member.name:
                    print(f"⚠️  Skipping suspicious path: {member.name}")
                    continue
                tar.extract(member, self.output_dir)
                self.imported_files.append(member.name)

        self._print_summary()
        return True

    def _print_summary(self) -> None:
        print(f"\n✅ Import complete!")
        print(f"   Files imported: {len(self.imported_files)}")

        if self.manifest:
            print(f"\n📊 Bundle Info:")
            print(f"   OKF Version: {self.manifest.get('okf_version', 'unknown')}")
            print(f"   Concepts: {self.manifest.get('statistics', {}).get('total_concepts', 0)}")
            types = self.manifest.get('statistics', {}).get('types', {})
            if types:
                print(f"   Types:")
                for t, count in sorted(types.items()):
                    print(f"     - {t}: {count}")
            export_time = self.manifest.get('export_time')
            if export_time:
                print(f"   Original export: {export_time}")

        print(f"\n📁 Output: {self.output_dir}")