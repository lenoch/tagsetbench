"""
Tokeny [word=".*ko" & tag="kA"], za kterými je pomlčka spojit spolu
s pomlčkou a následujícím tokenem do jednoho tokenu se značkou
z posledního, např. z:

architektonicko	architektonický	kA
-
stavebním	stavební	k2eAgFnPc3d1

udělat:

architektonicko-stavebním	architektonicko-stavební	k2eAgFnPc3d1
"""
from vertical import read_vertical


def architektonicko_stavebni(args, lines, output_file):
    architektonicko = None
    spojovnik = None
    for xml_tag, token in read_vertical(lines):
        if xml_tag:
            print(xml_tag.original_lines, file=output_file)
        elif architektonicko:
            if spojovnik:
                token['word'] = (architektonicko['word'] + '-' +
                                 token['word'])
                # Někdy druhé slovo lemma nemělo, ale to už jsem dal růčo.
                # Taky jsem zapomněl na .lower(), ale taky nevadilo.
                token['lemma'] = (architektonicko['word'] + '-' +
                                  token['lemma'])
                print(token.plain_vertical(), flush=True)
                architektonicko = None
                spojovnik = None
                print(token.plain_vertical(original_tag=True),
                      file=output_file)
            elif token['word'] == '-':
                spojovnik = token
            else:
                print('První slovo bylo OK, ale nebyl za ním spojovník. '
                      'Šlo o: {}'.format(architektonicko.plain_vertical()),
                      flush=True)
                print(architektonicko.plain_vertical(original_tag=True),
                      file=output_file)
                print(token.plain_vertical(original_tag=True),
                      file=output_file)
                architektonicko = None
        else:
            if (token['word'].lower().endswith('ko') and
                    token.get('k') == 'A'):
                architektonicko = token
                continue
            print(token.plain_vertical(original_tag=True),
                  file=output_file)
