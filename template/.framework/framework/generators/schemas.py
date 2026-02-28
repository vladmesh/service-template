"""Schema generator using datamodel-codegen as a library."""

import json
from pathlib import Path

from datamodel_code_generator import (
    DataModelType,
    Formatter,
    InputFileType,
    PythonVersion,
    generate,
)

from framework.generators.base import BaseGenerator
from framework.spec.loader import AllSpecs


class SchemasGenerator(BaseGenerator):
    """Generate Pydantic schemas from models.yaml."""

    def __init__(self, specs: AllSpecs, repo_root: Path) -> None:
        """Initialize with specs."""
        super().__init__(specs, repo_root)
        self.output_file = repo_root / "shared" / "shared" / "generated" / "schemas.py"

    def generate(self) -> list[Path]:
        """Generate Pydantic models from spec."""
        # Convert specs to JSON Schema
        json_schema = self.specs.models.to_json_schema()

        # Use datamodel-codegen as library
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        generate(
            input_=json.dumps(json_schema),
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            use_standard_collections=True,
            use_union_operator=True,
            use_schema_description=True,
            use_field_description=True,
            target_python_version=PythonVersion.PY_311,
            output=self.output_file,
            disable_timestamp=True,
            formatters=[Formatter.RUFF_FORMAT, Formatter.RUFF_CHECK],
        )

        # Read generated content and write back with header
        if self.output_file.exists():
            content = self.output_file.read_text()
            self.write_file(self.output_file, content)
            self.format_file(self.output_file)

        return [self.output_file]
