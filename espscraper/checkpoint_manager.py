import os
import json
import shutil
from abc import ABC, abstractmethod
from typing import Set, Tuple, Optional, Dict, Any, List

class AbstractCheckpointManager(ABC):
    @abstractmethod
    def get_scraped_ids_and_checkpoint(self) -> Tuple[Set[str], Optional[str], int]:
        pass
    @abstractmethod
    def write_checkpoint(self, last_valid_product_id: Optional[str], last_valid_line: int) -> None:
        pass
    @abstractmethod
    def read_checkpoint(self) -> Optional[Dict[str, Any]]:
        pass
    @abstractmethod
    def validate_and_truncate(self) -> Tuple[Set[str], Optional[str], int]:
        pass

class CheckpointManager(AbstractCheckpointManager):
    """
    Enhanced checkpoint manager with advanced validation and multi-object extraction.
    """
    def __init__(self, output_file: str, id_fields: Optional[List[str]] = None, backup: bool = True, schema: Optional[List[str]] = None, metadata_file: Optional[str] = None):
        self.output_file = output_file
        self.checkpoint_file = output_file + '.checkpoint'
        self.metadata_file = metadata_file or output_file.replace('.jsonl', '.meta.json')
        self.id_fields = id_fields or ['id', 'ProductID', 'productId']
        self.backup = backup
        self.schema = schema or self.id_fields
        self.invalid_lines: List[Tuple[int, str]] = []
        self.duplicate_ids: Set[str] = set()
        self.partial_lines: List[Tuple[int, str]] = []

    def _extract_id(self, obj: dict) -> Optional[str]:
        for field in self.id_fields:
            if field in obj and obj[field]:
                return str(obj[field])
        return None

    def _validate_schema(self, obj: dict) -> bool:
        return all(field in obj and obj[field] for field in self.schema)

    def _extract_json_objects(self, text: str) -> List[dict]:
        """
        Extract all valid JSON objects from a string using raw_decode.
        """
        decoder = json.JSONDecoder()
        idx = 0
        length = len(text)
        objects = []
        while idx < length:
            try:
                obj, end = decoder.raw_decode(text, idx)
                objects.append(obj)
                idx = end
                while idx < length and text[idx] in ' \r\n\t':
                    idx += 1
            except json.JSONDecodeError:
                break
        return objects

    def get_scraped_ids_and_checkpoint(self, scan_all: bool = True, keep_last_duplicate: bool = False) -> Tuple[Set[str], Optional[str], int]:
        """
        Scans the output file for all valid JSON objects (multi-object extraction), logs/reporting invalid/corrupted/partial lines,
        detects duplicates, optionally backs up and atomically truncates the file, and writes a checkpoint.
        Returns (scraped_ids, last_valid_product_id, last_valid_line).
        """
        scraped_ids = set()
        id_to_line = {}
        valid_lines = []
        last_valid_product_id = None
        self.invalid_lines.clear()
        self.partial_lines.clear()
        self.duplicate_ids.clear()
        if not os.path.exists(self.output_file):
            return scraped_ids, None, 0
        # Backup before truncation
        if self.backup:
            shutil.copy2(self.output_file, self.output_file + '.bak')
        with open(self.output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.rstrip('\n')
                if not line.strip():
                    continue
                found_any = False
                for obj in self._extract_json_objects(line):
                    found_any = True
                    if not self._validate_schema(obj):
                        self.invalid_lines.append((i, line))
                        continue
                    pid = self._extract_id(obj)
                    if pid is None:
                        self.invalid_lines.append((i, line))
                        continue
                    if pid in id_to_line:
                        self.duplicate_ids.add(pid)
                        if keep_last_duplicate:
                            id_to_line[pid] = (i, json.dumps(obj))
                    else:
                        id_to_line[pid] = (i, json.dumps(obj))
                if not found_any:
                    # No valid JSON object found in this line
                    self.invalid_lines.append((i, line))
                    if not scan_all:
                        break
        # Build valid_lines list (keep first or last duplicate)
        for pid, (i, line) in id_to_line.items():
            valid_lines.append((i, line, pid))
        valid_lines.sort()  # preserve file order
        # Write valid lines atomically
        tmp_file = self.output_file + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as out:
            for i, line, pid in valid_lines:
                out.write(line + '\n')
                scraped_ids.add(pid)
                last_valid_product_id = pid
        os.replace(tmp_file, self.output_file)
        # Write checkpoint
        self.write_checkpoint(last_valid_product_id, len(valid_lines))
        return scraped_ids, last_valid_product_id, len(valid_lines)

    def write_checkpoint(self, last_valid_product_id: Optional[str], last_valid_line: int) -> None:
        checkpoint = {
            'last_valid_product_id': last_valid_product_id,
            'last_valid_line': last_valid_line
        }
        with open(self.checkpoint_file, 'w') as cf:
            json.dump(checkpoint, cf)

    def read_checkpoint(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.checkpoint_file):
            return None
        with open(self.checkpoint_file, 'r') as cf:
            try:
                return json.load(cf)
            except Exception:
                return None

    def validate_and_truncate(self) -> Tuple[Set[str], Optional[str], int]:
        checkpoint = self.read_checkpoint()
        if checkpoint is None:
            return self.get_scraped_ids_and_checkpoint()
        scraped_ids, last_valid_product_id, last_valid_line = self.get_scraped_ids_and_checkpoint()
        if checkpoint.get('last_valid_product_id') != last_valid_product_id or checkpoint.get('last_valid_line') != last_valid_line:
            return self.get_scraped_ids_and_checkpoint()
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as mf:
                    meta = json.load(mf)
                if 'resultsTotal' in meta and meta['resultsTotal'] != len(scraped_ids):
                    print(f"[Metadata] Warning: resultsTotal ({meta['resultsTotal']}) does not match file ({len(scraped_ids)})")
            except Exception as e:
                print(f"[Metadata] Error reading metadata: {e}")
        return scraped_ids, last_valid_product_id, last_valid_line

    def report_issues(self):
        if self.invalid_lines:
            print("[Invalid lines detected]:")
            for i, line in self.invalid_lines:
                print(f"  Line {i}: {line}")
        if self.partial_lines:
            print("[Partial/incomplete JSON lines]:")
            for i, line in self.partial_lines:
                print(f"  Line {i}: {line}")
        if self.duplicate_ids:
            print(f"[Duplicate IDs detected]: {self.duplicate_ids}") 