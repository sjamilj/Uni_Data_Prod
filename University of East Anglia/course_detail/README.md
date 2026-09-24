# course_detail/

Save **one sample course page per programme** to configure `COURSE_CLEAN_BLOCKS` in `code/.env`.

## Filename pattern

```
{Course Title} - {Award} - UEA.html
```

## UEA samples

| Programme | Example URL | Filename |
|-----------|-------------|----------|
| Undergraduate | https://www.uea.ac.uk/course/undergraduate/bsc-actuarial-science | `Actuarial Science - BSc (Hons) - UEA.html` |
| Postgraduate taught | https://www.uea.ac.uk/course/postgraduate/msc-computing-science | `Computing Science - MSc - UEA.html` |

Template stubs (`sample-*.html`, `course-details.html`) are placeholders — replace with real browser saves.

Live page hooks already in `code/ENV.MD`: `h1.course-title`, `#entry_requirements`, `#fees_funding`.
