"""Persistent, content-addressed story preparation, separate from play sessions."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from uuid import uuid4

from story_game import GeneratedScenario


class PackCache:
    def __init__(self, directory, store, settings, extract, chunk, build):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.store, self.settings = store, settings
        self.extract, self.chunk, self.build = extract, chunk, build
        self.lock = RLock()
        self.pack_locks = {}

    def prepare(self, raw, filename):
        extension = Path(filename).suffix.lower()
        signature = json.dumps(self.settings, sort_keys=True, ensure_ascii=False).encode()
        key = hashlib.sha256(signature + b"\0" + extension.encode() + b"\0" + raw).hexdigest()
        path = self.directory / (key + ".json")
        with self.lock:
            pack_lock = self.pack_locks.setdefault(key, RLock())
        with pack_lock:
            cached = None
            if path.exists():
                try:
                    cached = json.loads(path.read_text(encoding="utf-8"))
                    scenario = GeneratedScenario.model_validate(cached["scenario"])
                    if cached["key"] != key or not cached["document"] or not cached["ids"]:
                        cached = None
                    elif not isinstance(cached["brief"], dict):
                        cached = None
                except (ValueError, KeyError, TypeError):
                    cached = None

            if cached is not None:
                present = set(self.store.get(ids=cached["ids"])["ids"])
                if present == set(cached["ids"]):
                    return {**cached, "scenario": scenario, "cache_hit": True, "chunks_added": 0}

            with TemporaryDirectory() as directory:
                source = Path(directory) / ("story" + extension)
                source.write_bytes(raw)
                docs = self.extract(source)
            document = "\n\n".join(doc.page_content for doc in docs).strip()
            if not document or len(document) > 20000:
                raise ValueError("텍스트를 추출할 수 없거나 20,000자를 넘는 문서입니다.")
            chunks = self.chunk(docs)
            if not chunks:
                raise ValueError("문서에서 검색할 내용을 찾을 수 없습니다.")
            if cached is None:
                scenario, brief = self.build(document)
            else:
                # Restore a missing vector index without paying for story analysis again.
                brief = cached["brief"]
            ids = [f"{key}:{index}" for index in range(len(chunks))]
            # Vector identity excludes scenario-parser/model settings. Exact chunk text
            # and embedding collection determine whether vectors can be reused.
            vector_signature = json.dumps({"embedding": self.settings.get("embedding"),
                "chunks": [c.page_content for c in chunks]}, sort_keys=True, ensure_ascii=False)
            vector_key = hashlib.sha256(vector_signature.encode()).hexdigest()
            vector_path = self.directory / ("vectors-" + vector_key + ".json")
            vector_record = None
            candidates = [vector_path] if vector_path.exists() else list(self.directory.glob("*.json"))
            for candidate in candidates:
                try:
                    old = json.loads(candidate.read_text(encoding="utf-8"))
                    if "embedding" in old and old["embedding"] != self.settings.get("embedding"):
                        continue
                    old_ids = old["ids"]
                    found = self.store.get(ids=old_ids, include=["documents", "metadatas"])
                    by_id = dict(zip(found["ids"], found["documents"]))
                    if ([by_id.get(i) for i in old_ids] == [c.page_content for c in chunks]
                            and len(old_ids) == len(chunks)):
                        vector_record = {"ids": old_ids, "vector_key": old.get("vector_key", old["key"])}
                        break
                except (ValueError, KeyError, TypeError):
                    continue
            if vector_record:
                ids = vector_record["ids"]
                vector_key = vector_record["vector_key"]
            else:
                ids = [f"{vector_key}:{index}" for index in range(len(chunks))]
            record = {"key": key, "document": document, "scenario": scenario.model_dump(),
                      "brief": brief, "ids": ids, "vector_key": vector_key,
                      "embedding": self.settings.get("embedding")}
            # Save analysis first so a failed embedding request can be retried cheaply.
            temporary = path.with_suffix(f".{uuid4().hex}.tmp")
            try:
                temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            if not vector_record:
                for index, chunk in enumerate(chunks):
                    chunk.metadata.update(pack_id=vector_key, source=filename,
                                          chunk_index=index, chunk_id=ids[index])
                self.store.add_documents(chunks, ids=ids)
            if set(self.store.get(ids=ids)["ids"]) != set(ids):
                raise RuntimeError("스토리팩 벡터 저장을 완료하지 못했습니다.")
            vector_path.write_text(json.dumps({"key": vector_key, "vector_key": vector_key,
                "ids": ids, "embedding": self.settings.get("embedding")}), encoding="utf-8")
            return {**record, "scenario": scenario, "cache_hit": False,
                    "chunks_added": 0 if vector_record else len(ids)}
