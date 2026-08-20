"""JUnit XML Result Exporter."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List


def export_to_junit_xml(results_data: List[Dict[str, Any]], output_path: str) -> None:
    """Exports test suite execution results to JUnit XML format for CI/CD integration."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    testsuite = ET.Element("testsuite", name="XiL_TestSuite", tests=str(len(results_data)))

    for result in results_data:
        testcase = ET.SubElement(
            testsuite,
            "testcase",
            name=result.get("test_name", "UnknownTest"),
            classname="ev_xil.tests",
        )
        if not result.get("passed", False):
            failure = ET.SubElement(testcase, "failure", message=result.get("verdict", "FAILED"))
            failure.text = result.get("error", "Assertion failed during execution")

    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ", level=0)
    tree.write(path, encoding="utf-8", xml_declaration=True)
