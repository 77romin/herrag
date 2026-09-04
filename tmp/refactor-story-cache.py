from pathlib import Path
p=Path('servers/story_api.py')
s=p.read_text(encoding='utf-8')
start=s.index('                response = backend.llm.invoke([')
end=s.index('                chunks = backend.chunk_documents(docs)', start)
build=s[start:end]
build='\n'.join(line[12:] if line.startswith('            ') else line for line in build.splitlines())
# Make the existing parser a reusable callback without changing its instructions.
head='''def build_scenario(document, backend):
'''+build+'''\n    return scenario, brief


'''
a=s.index('def install_story_api(app, backend):')
b=s.index('    @app.post("/upload")', a)
new='''def install_story_api(app, backend):
    cache = None

    def get_cache():
        nonlocal cache
        if cache is None:
            from langchain_chroma import Chroma
            # Use a separate collection when the embedding provider/model changes.
            embedding_signature = hashlib.sha256(json.dumps({
                "model": backend.EMBEDDING_MODEL_NAME, "provider": backend.BASE_URL
            }, sort_keys=True).encode()).hexdigest()[:16]
            store = Chroma(collection_name="story_packs_" + embedding_signature,
                           embedding_function=backend.embeddings,
                           persist_directory=str(backend.DATA_DIR.parent / "story_vectors"))
            parser_signature = hashlib.sha256((inspect.getsource(build_scenario)
                + inspect.getsource(review_brief)
                + json.dumps(GeneratedScenario.model_json_schema(), sort_keys=True)
                + inspect.getsource(backend.chunk_documents)
                + inspect.getsource(backend.extract_documents)).encode()).hexdigest()
            cache = PackCache(backend.DATA_DIR.parent / "story_cache", store,
                {"parser": parser_signature, "model": backend.GPT_MODEL,
                 "embedding": embedding_signature, "size": backend.CHUNK_SIZE,
                 "overlap": backend.OVERLAP, "version": 1},
                backend.extract_documents, backend.chunk_documents,
                lambda document: build_scenario(document, backend))
        return cache

    def prepare_pack(raw, name):
        return get_cache().prepare(raw, name)

    app.state.prepare_story_pack = prepare_pack

'''
s=s[:a]+head+new+s[b:]
a=s.index('                with TemporaryDirectory() as directory:',s.index('@app.post("/upload")'))
b=s.index('            except HTTPException:',a)
s=s[:a]+'''                prepared = prepare_pack(raw, name)
                result = games.activate(session, name, prepared["document"],
                    prepared["scenario"], revision, public_brief=prepared["brief"],
                    pack_id=prepared["key"])
                return {"success": True, "message": "새 시나리오를 시작합니다.",
                        "cache_hit": prepared["cache_hit"],
                        "chunks_added": 0 if prepared["cache_hit"] else len(prepared["ids"]),
                        **result}
'''+s[b:]
s=s.replace('                discard(revision)\n','')
s=s.replace('backend.vectorstore.similarity_search_with_relevance_scores(', 'get_cache().store.similarity_search_with_relevance_scores(')
s=s.replace('filter={"scenario_id": game.revision}', 'filter={"pack_id": game.pack_id}')
s=s.replace('                if result["ended"]:\n                    discard(str(req.revision))\n','')
s=s.replace('            previous = games.games.pop(str(req.session_id), None)\n            if previous:\n                discard(previous.revision)', '            games.games.pop(str(req.session_id), None)')
s=s.replace('from tempfile import TemporaryDirectory\n','')
s=s.replace('import logging\n','import logging\nimport hashlib\nimport inspect\n')
s=s.replace('from story_brief import review_brief\n','from story_brief import review_brief\nfrom story_cache import PackCache\n')
p.write_text(s,encoding='utf-8')
