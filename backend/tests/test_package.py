import hashlib
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.repository import JsonRepository


def test_package_keeps_snapshot_manifest_and_captured_provenance_consistent(tmp_path):
    with TestClient(create_app(JsonRepository(tmp_path))) as client:
        client.post('/api/cases/demo', json={})
        client.post('/api/cases/demo-case/investigate', json={})
        package = client.get('/api/cases/demo-case/package').json()
        assert package['package_type'] == 'kinfold_research_package'
        assert package['manifest']['digest'] == client.get('/api/cases/demo-case/manifest').json()['digest']
        assert package['snapshot']['case'] == package['manifest']['manifest']['case']
        assert all(p['captured_hash_matches'] for p in package['source_provenance'])
        added = client.post('/api/cases/demo-case/documents', json={'name':'Synthetic note.txt','text':'Synthetic source text.'}).json()['documents'][-1]
        assert added['provenance']['origin'] == 'user_upload'
        assert added['provenance']['received_at'].endswith('Z')
        assert added['provenance']['text_sha256'] == hashlib.sha256(b'Synthetic source text.').hexdigest()
        # External storage modification changes the manifest but never rewrites the captured fingerprint.
        repo=client.app.state.repository
        state=repo.get('demo-case');state['documents'][0]['text']+='\nAltered after capture.';repo.put(state)
        altered=client.get('/api/cases/demo-case/package').json()
        assert altered['source_provenance'][0]['captured_hash_matches'] is False
