import importlib.util
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "shared"))

from clean_config import CleanConfigLoader
from download_and_clean_course_pages import CourseMarkdownBuilder

_spec = importlib.util.spec_from_file_location(
    "uel_cleanup",
    Path(__file__).resolve().parent / "course_markdown_cleanup.py",
)
uel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uel)

SAMPLE = """
<html><body><main>
<h1>Criminology with Law BA (Hons)</h1>
<div class="course-option-details__list-item">
  <span class="visually-hidden-text">International applicant full time</span>
  <span class="attendance-type-yr">3 years full time</span>
  <span class="fee-type">Year 1: £15,000</span>
</div>
<button class="course-options__btn">September 2026</button>
<dialog id="entry-requirements-1" class="modal-entry entry-requirements-modal">
  <div id="entry-req-details-1">
    <div class="accordion-item">
      <h3 class="coh-heading">Academic requirements</h3>
      <div class="accordion-body"><div class="rich-txt-custom"><p>112 UCAS points</p></div></div>
    </div>
    <div class="accordion-item">
      <h3 class="coh-heading">English Language requirements</h3>
      <div class="accordion-body"><div class="rich-txt-custom"><p>IELTS 6.0 overall</p></div></div>
    </div>
  </div>
  <div id="entry-req-details-2">
    <div class="accordion-item">
      <h3 class="coh-heading">Academic requirements</h3>
      <div class="accordion-body"><div class="rich-txt-custom"><p>64 UCAS points</p></div></div>
    </div>
    <div class="accordion-item">
      <h3 class="coh-heading">English Language requirements</h3>
      <div class="accordion-body"><div class="rich-txt-custom"><p>IELTS 5.5 overall</p></div></div>
    </div>
  </div>
</dialog>
</main></body></html>
"""


def main() -> None:
    levels = uel.study_levels_for_course_html(
        SAMPLE,
        course_url="https://www.uel.ac.uk/undergraduate/courses/example",
        default_levels=["undergraduate"],
    )
    assert levels == ["undergraduate", "foundation"]

    code_dir = Path(__file__).resolve().parent
    cfg = CleanConfigLoader.load(code_dir)
    md = CourseMarkdownBuilder.from_config(SAMPLE, cfg, code_dir)
    full = uel.cleanup_course_markdown_uni(md)
    assert "112 UCAS" in full and "64 UCAS" in full
    ug = uel.extra_clean_course_markdown_uni(full, study_level="undergraduate")
    fy = uel.extra_clean_course_markdown_uni(full, study_level="foundation")
    assert "112 UCAS" in ug and "IELTS 6.0" in ug
    assert "64 UCAS" in fy and "IELTS 5.5" in fy
    assert "112 UCAS" not in fy
    print("OK")


if __name__ == "__main__":
    main()
