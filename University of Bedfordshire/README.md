# University of Bedfordshire (unit-31 / beds)

| Item | Value |
|------|--------|
| Registry | `unit-31` · slug `beds` |
| Strategy | `DEGREE_SCOPED_PAGINATED` · `DegreeScopedPaginated.csv` |
| Base URL | https://www.beds.ac.uk |

## Listing (React course search)

Course catalogues live under `/howtoapply/courses/{programme}/` (filter UI in-page, not classic HTML pagination).

| Programme | Listing URL (seed) |
|-----------|-------------------|
| Postgraduate | [Postgraduate courses](https://www.beds.ac.uk/howtoapply/courses/postgraduate/) |
| Undergraduate | TBD |
| Foundation | TBD |
| Postgraduate research | TBD |

Save browser HTML to `course_listing/postgraduate.html` when tuning scrape selectors.

## Next (operator)

1. Fill remaining rows in `Template.csv` → `python shared/build_university_from_template.py --template-csv "University of Bedfordshire/Template.csv"`
2. Save `uni_req/*.html` and sample `course_detail/*.html`
3. Implement or configure React listing scrape (shared — pending)

```powershell
.\scripts\commit-uni.cmd -Pick beds -Type feat -Summary "bootstrap beds React listing shell"
```
