# TODO: když tuhle modifikaci nechám, tak ji můžu krásně deklarovat v configure
#       jako poslední z řetězu modifikací na trénovacím korpusu!
# NOTE: abych nemusel ukládat dočasnej korpus, mohl bych vytvořit pojmeno-
#       vanou rouru, nechat na druhé straně běžet program a po natrénování
#       ho odstřelit, ale to je asi složitý, takže se na to zatím vyprdnu;
#       a hlavně nemusí trénovací program číst jen sekvenčně

from . import rftagger, Modifier


class rftagger_preprocess(Modifier):
    def __call__(self, sentence):
        sentence.opening_tag = ''
        sentence.closing_tag = ''

        for token in sentence.tokens:
            self.use_rftagger_output_format(token)
            self.mark_modified(token)

    def use_rftagger_output_format(self, token):
        """
        Bind rftagger.token_lines as a Token .lines method.
        """
        token.lines = rftagger.token_lines.__get__(token)
