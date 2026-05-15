# POSN Physics Notes

Thai physics notes for POSN Physics Camp 1, written in LaTeX.

The document is built from `main.tex`, with shared layout and custom environments in `structure.tex`. Chapter files live in `chapters/`.

## Requirements

- A TeX distribution with XeLaTeX, such as TeX Live or MiKTeX
- `latexmk` for the recommended build command
- The bundled TH Sarabun New fonts in `thsarabun/`

This project uses Thai text and `fontspec`, so compile with XeLaTeX instead of pdfLaTeX.

## Build

Recommended:

```sh
latexmk -xelatex main.tex
```

Alternative:

```sh
xelatex main.tex
```

Run the command twice if references, table of contents entries, or page numbers need another pass.

To clean generated files:

```sh
latexmk -c
```

## Project Structure

```text
.
├── main.tex
├── structure.tex
├── chapters/
│   ├── chapter-02-linear-motion.tex
│   ├── chapter-03-vectors.tex
│   ├── chapter-04-two-dimensional-motion.tex
│   ├── chapter-05-laws-of-motion.tex
│   └── chapter-06-circular-motion.tex
├── thsarabun/
├── img/
└── Ref/
```

## Editing Chapters

Enable or disable chapters by editing the `\input{...}` lines near the end of `main.tex`.

Current active chapters:

- `chapters/chapter-04-two-dimensional-motion.tex`
- `chapters/chapter-05-laws-of-motion.tex`

## Notes

- Generated build files and PDFs are ignored by Git.
- `img/` and `Ref/` are intended for local images and references and are ignored by Git.
- The document footer currently credits `Tames Thanakrit Damduan`.
