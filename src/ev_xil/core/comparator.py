"""Equivalence & Cross-Level Comparator Module for MIL, SIL, HIL, and VIL Verification."""

import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


def assert_equivalent(reference: float, candidate: float, tolerance: float = 0.5) -> None:
    """Asserts that absolute numerical error between reference and candidate is within tolerance."""
    error = abs(float(reference) - float(candidate))
    assert error <= tolerance, (
        f"Equivalence Assertion Failed: Error {error:.4f} exceeds limit {tolerance:.4f} "
        f"(Reference={reference}, Candidate={candidate})"
    )


class EquivalenceComparator:
    """Utility class for comparing numerical signals and time-series data between XiL execution profiles."""

    @staticmethod
    def compare_scalar(val_a: float, val_b: float, tolerance: float = 0.5) -> bool:
        """Computes absolute error between two scalar values and validates against tolerance."""
        val_a = float(val_a)
        val_b = float(val_b)
        absolute_error = abs(val_a - val_b)
        is_equivalent = absolute_error <= tolerance

        if not is_equivalent:
            logger.warning(
                f"Equivalence mismatch: val_a={val_a}, val_b={val_b}, "
                f"absolute_error={absolute_error:.5f} exceeds tolerance={tolerance}"
            )
        else:
            logger.info(
                f"Equivalence verified: val_a={val_a}, val_b={val_b}, "
                f"absolute_error={absolute_error:.5f} <= tolerance={tolerance}"
            )

        return is_equivalent

    @staticmethod
    def evaluate_scalar(
        name_a: str, val_a: float, name_b: str, val_b: float, tolerance: float = 0.5
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluates scalar equivalence and returns structured comparison dictionary."""
        abs_err = abs(float(val_a) - float(val_b))
        is_eq = abs_err <= tolerance
        result = {
            "name_a": name_a,
            "val_a": val_a,
            "name_b": name_b,
            "val_b": val_b,
            "absolute_error": abs_err,
            "tolerance": tolerance,
            "is_equivalent": is_eq,
            "verdict": "EQUIVALENT" if is_eq else "MISMATCH",
        }
        return is_eq, result

    @staticmethod
    def print_equivalence_result(
        signal_name: str,
        ref_name: str,
        ref_val: float,
        cand_name: str,
        cand_val: float,
        tolerance: float = 0.5,
    ) -> str:
        """Formats and prints standardized B2B Equivalence Result block."""
        ref_val = float(ref_val)
        cand_val = float(cand_val)
        error = abs(ref_val - cand_val)
        status = "PASS" if error <= tolerance else "FAIL"

        lines = [
            f"{ref_name}/{cand_name} equivalence",
            f"{signal_name}",
            f"{ref_name:4} : {ref_val:.2f}",
            f"{cand_name:4} : {cand_val:.2f}",
            f"Error: {error:.2f}",
            f"Limit: {tolerance:.2f}",
            f"{status}",
        ]
        report_text = "\n".join(lines)
        print(report_text)
        return report_text


class CrossLevelComparator:
    """Multi-level XiL cross-comparison engine for MIL vs SIL vs HIL vs VIL verification."""

    @staticmethod
    def compare_cross_levels(
        level_results: Dict[str, float], tolerance: float = 0.5
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Compares signal values pairwise across MIL, SIL, HIL, VIL execution levels."""
        levels = list(level_results.keys())
        comparison_matrix = []
        all_passed = True

        for i in range(len(levels) - 1):
            level_a = levels[i]
            level_b = levels[i + 1]
            val_a = float(level_results[level_a])
            val_b = float(level_results[level_b])
            error = abs(val_a - val_b)
            passed = error <= tolerance

            if not passed:
                all_passed = False

            comparison_matrix.append({
                "pair": f"{level_a} vs {level_b}",
                "level_a": level_a,
                "val_a": val_a,
                "level_b": level_b,
                "val_b": val_b,
                "error": error,
                "tolerance": tolerance,
                "verdict": "EQUIVALENT" if passed else "MISMATCH",
            })

        return all_passed, comparison_matrix

    @staticmethod
    def print_cross_level_report(
        signal_name: str, level_results: Dict[str, float], tolerance: float = 0.5
    ) -> None:
        """Prints a standardized Cross-Level Result Comparison report table."""
        all_passed, matrix = CrossLevelComparator.compare_cross_levels(level_results, tolerance)

        print("\n==========================================================================")
        print(f"      Cross-Level Result Comparison Report: {signal_name}")
        print("==========================================================================")
        print(" Level  | Measured Value | Reference Pair | Delta Error | Limit | Verdict")
        print("--------------------------------------------------------------------------")

        for lvl, val in level_results.items():
            print(f" {lvl:6} | {val:14.2f} | -              | -           | -     | BASE")

        print("--------------------------------------------------------------------------")
        for item in matrix:
            print(
                f" PAIR   | {item['pair']:14} | {item['val_a']:.2f} -> {item['val_b']:.2f} | "
                f"{item['error']:11.4f} | {tolerance:5.2f} | {item['verdict']}"
            )
        print("--------------------------------------------------------------------------")
        print(f" Cross-Level Equivalence Verdict: {'PASSED (ALL LEVELS CONSISTENT)' if all_passed else 'FAILED'}")
        print("==========================================================================\n")
