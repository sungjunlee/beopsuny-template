"""
Data integrity tests for permits.yaml and related data files.

Validates:
- YAML syntax
- Required fields
- Law ID format
- Cross-references
"""
import sys
from pathlib import Path

import pytest
import yaml


class TestPermitsYaml:
    """Tests for permits.yaml data integrity."""

    @pytest.fixture
    def permits_data(self, permits_yaml_path):
        """Load permits.yaml data."""
        with open(permits_yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_yaml_syntax_valid(self, permits_yaml_path):
        """Should be valid YAML syntax."""
        with open(permits_yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_required_top_level_keys(self, permits_data):
        """Should have required top-level keys."""
        assert 'categories' in permits_data
        assert 'items' in permits_data  # items, not permits

    def test_categories_not_empty(self, permits_data):
        """Should have at least one category."""
        assert len(permits_data['categories']) > 0

    def test_permits_not_empty(self, permits_data):
        """Should have at least one permit."""
        assert len(permits_data['items']) > 0

    def test_all_permits_have_required_fields(self, permits_data):
        """All permits should have required fields."""
        required_fields = {'id', 'name', 'category', 'law'}
        for permit in permits_data['items']:
            for field in required_fields:
                assert field in permit, f"Permit {permit.get('id', 'unknown')} missing {field}"

    def test_permit_ids_unique(self, permits_data):
        """All permit IDs should be unique."""
        ids = [p['id'] for p in permits_data['items']]
        assert len(ids) == len(set(ids)), "Duplicate permit IDs found"

    def test_permit_id_format(self, permits_data):
        """Permit IDs should follow format 'permit-NNN'."""
        import re
        pattern = re.compile(r'^permit-\d{3}$')
        for permit in permits_data['items']:
            assert pattern.match(permit['id']), f"Invalid permit ID format: {permit['id']}"

    def test_categories_referenced_exist(self, permits_data):
        """All permit categories should exist in categories list."""
        valid_categories = {c['id'] for c in permits_data['categories']}
        for permit in permits_data['items']:
            assert permit['category'] in valid_categories, \
                f"Permit {permit['id']} has invalid category: {permit['category']}"

    def test_minimum_permit_count(self, permits_data):
        """Should have at least 25 permits (target: 30)."""
        assert len(permits_data['items']) >= 25


class TestLawIndexYaml:
    """Tests for law_index.yaml data integrity."""

    @pytest.fixture
    def law_index_data(self, law_index_yaml_path):
        """Load law_index.yaml data."""
        with open(law_index_yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_yaml_syntax_valid(self, law_index_yaml_path):
        """Should be valid YAML syntax."""
        with open(law_index_yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_major_laws_section(self, law_index_data):
        """Should have major_laws section."""
        assert 'major_laws' in law_index_data

    def test_major_laws_not_empty(self, law_index_data):
        """Should have at least one major law."""
        assert len(law_index_data['major_laws']) > 0

    def test_law_id_format(self, law_index_data):
        """Law IDs should be 6-digit strings."""
        import re
        pattern = re.compile(r'^\d{6}$')
        for law_name, law_id in law_index_data['major_laws'].items():
            assert pattern.match(str(law_id)), \
                f"Invalid law ID format for {law_name}: {law_id}"


class TestChecklistsData:
    """Tests for checklist YAML files."""

    def test_all_checklists_valid_yaml(self, checklists_dir):
        """All checklist files should be valid YAML."""
        for yaml_file in checklists_dir.glob('*.yaml'):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            assert data is not None, f"Invalid YAML: {yaml_file.name}"

    def test_checklists_have_name(self, checklists_dir):
        """All checklists should have name field."""
        for yaml_file in checklists_dir.glob('*.yaml'):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            assert 'name' in data, f"{yaml_file.name} missing name"

    def test_checklist_items_have_id_and_content(self, checklists_dir):
        """Checklists with 'items' key should have id and content field per item."""
        for yaml_file in checklists_dir.glob('*.yaml'):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            # Only test files that have 'items' key
            items = data.get('items', [])
            if items:
                for item in items:
                    assert 'id' in item, f"{yaml_file.name} item missing id"
                    # Some checklists use 'task', others use 'question'
                    has_content = 'task' in item or 'question' in item
                    assert has_content, f"{yaml_file.name} item {item.get('id')} missing task/question"

    def test_minimum_checklist_count(self, checklists_dir):
        """Should have at least 8 checklists."""
        checklist_files = list(checklists_dir.glob('*.yaml'))
        assert len(checklist_files) >= 8, f"Found only {len(checklist_files)} checklists"


class TestClauseReferencesData:
    """Tests for clause_references.yaml data integrity."""

    @pytest.fixture
    def clauses_data(self):
        """Load clause_references.yaml data."""
        clauses_path = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "assets" / "clause_references.yaml"
        with open(clauses_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_yaml_syntax_valid(self, clauses_data):
        """Should be valid YAML syntax."""
        assert clauses_data is not None

    def test_has_clauses_section(self, clauses_data):
        """Should have clauses section."""
        assert 'clauses' in clauses_data

    def test_minimum_clause_count(self, clauses_data):
        """Should have at least 50 clauses."""
        # clauses is a dict, not a list
        assert len(clauses_data['clauses']) >= 50

    def test_clauses_have_required_fields(self, clauses_data):
        """All clauses should have required fields."""
        # clauses is dict with id as key
        required_fields = {'name_ko', 'name_en', 'category'}
        for clause_id, clause in clauses_data['clauses'].items():
            for field in required_fields:
                assert field in clause, f"Clause {clause_id} missing {field}"
