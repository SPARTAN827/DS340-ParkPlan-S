# Paper build and review notes

November 15, 2026 | Jesse Zhang and Yongqi Sheng

## Changes from Week 10

The Week 12 paper keeps the earlier Abstract, Introduction, Related Work and Methodology, adds Section 3.5 on the contribution, and includes Evaluation and Conclusion. The evaluation covers paired time comparisons, all-attempt outcomes, calibration, the shared-order ablation, action-value diagnostics and six input settings.

The reported results come from the existing study. D0 minus R is -6.36 modeled minutes on 118 jointly completed dates, with a seven-date block interval of [-13.73, 0.36]. D0 and R complete 126 and 128 of 165 dates. The 15.48-minute F-minus-D0 difference uses a separate set of 105 jointly completed dates.

Table values were checked against the full-precision summary files. For example, the illustrative sensitivity interval rounds to [-7.42, 1.94]; rounding the report's already rounded values can give a different endpoint. The six references retain their previously checked metadata. The introduction's route example concerns two still-unvisited rides after completing a different ride.

## PDF and source checks

- Eight US Letter pages, including references; within the guide's eight-page main-body maximum.
- Official ICML style files unchanged. Names and coursework notice replace the conference metadata.
- Tectonic 0.17.0 with OT1 encoding; embedded Nimbus/Times body text at 9.96 PDF points.
- All pages reviewed for tables, equations, citations, footnotes and clipping.
- No overfull boxes, unresolved references, font substitution, author placeholders or duplicate destinations. Ordinary underfull justification warnings remain.
- Nine-file source ZIP passes CRC and file-content checks. An offline build from a fresh extraction matches the PDF's text and rendered pages at 1.4x resolution.

The source ZIP includes its template provenance record. Build verification used local tools; the Overleaf web interface is outside these checks. AI-assisted editing and review were part of the development process described in the [project README](../../README.md#project-development).

## Interpretation

The separate ADAPT reproduction is a UAV experiment, not evidence of park time savings. The park results remain exploratory and use assumed walking/service inputs. The six sensitivity settings reuse the same wait records; they are not comparisons across independent datasets.

## PDF properties correction

The PDF title now preserves the space before “for Six Theme-Park Rides,” and the subject identifies this as a DS 340W course project instead of the template’s ICML proceedings default. Jesse Zhang and Yongqi Sheng remain the named authors. All eight pages have identical text and rendered pixels to the preceding PDF; a fresh source-package build also matches.
