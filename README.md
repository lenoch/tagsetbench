# tagsetbench

This project is aimed to evaluate the effects of changes to a corpus
annotation on POS tagging, with cross-validation.

The Czech corpus DESAM (with its attributive tagset) is assumed, as well
[RFTagger][2]. Originally developed as part of my [master’s thesis][1].


MIT licensed, except the 3rd party files which have their own licences.

## TODO
Currently, the code includes parts of my (unreleased) chart parser “ijáček”.
It should be released as well and the common code should be shared across the
projects.

## Usage notes
To be written, but you need at least Python 3.5, [RFTagger][2], and GNU Make.
Plus the DESAM corpus or any corpus using the Czech attributive tagset. The
tagset is employed by a free morphological analyzer [Majka][3].

There may be some useful description in [readme.html](readme.html).

[1]:https://is.muni.cz/auth/th/359558/ff_m_a2/tagsetbench.pdf
[2]:http://www.cis.uni-muenchen.de/~schmid/tools/RFTagger/
[3]:https://nlp.fi.muni.cz/ma/

(Optional) Python 3 packages, available in Arch Linux AUR:
* `python-beautifulsoup4 4.5.1-1` (required by `compare_evaluation.py`)
* `python-tabulate` (`convert_to_latex.py`, just a helper script)
* `python-colorlog` (optional)
* `python-pygments` (`pygments_lexer.py`, also an unnecessary part)

## Further notes

Firefox >= 51 is advised for colourful emojis to help navigate generated HTML
tables with better visual cue than just shapes/glyphs.

Czech comments in the code do not contain important stuff.
