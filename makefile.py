from tagsetbench import ShellPath


class Makefile:
    def __init__(self, path=None, recipes=None):
        self.path = path  # TODO: všechny budou ve working_dir, stačí 'name'
        # TODO: self.declarations? (pomocí slovníku, aby na ně šlo odkazovat)
        #       split_corpora=' \\\n\t'.join(self.split_corpora),
        #       """SPLIT_CORPORA = \
        #               {split_corpora}""".format(split_corpora)
        self.recipes = recipes or []

    def write(self):
        with self.path.open('w') as f:
            delete_on_error_targets = []
            for recipe in self.recipes:
                if isinstance(recipe, MakefileRecipe) and \
                        recipe.delete_on_error:
                    delete_on_error_targets.extend(recipe.targets)

            if delete_on_error_targets:
                delete_on_error_recipe = MakefileRecipe(
                    targets=['.DELETE_ON_ERROR'],
                    dependencies=delete_on_error_targets,
                )
                for line in delete_on_error_recipe.lines():
                    print(line, file=f)
                print(file=f)

            for recipe in self.recipes:
                if isinstance(recipe, MakefileRecipe):
                    for line in recipe.lines():
                        print(line, file=f)
                else:
                    print(recipe, file=f)
                print(file=f)


class MakefileRecipe:
    def __init__(self, targets=None, dependencies=None, commands=None,
                 delete_on_error=True):
        self.targets = targets or []
        self.dependencies = dependencies or []
        self.commands = commands or []
        self.delete_on_error = delete_on_error

    def lines(self):
        """
        Solution to building multiple targets only once was inspired by
        https://www.cmcrossroads.com/article/rules-multiple-outputs-gnu-make
        """
        # TODO: 'make' moc nezvládá mezery, ale můžu ještě jednou prubnout ' '
        if len(self.targets) > 1:
            for target, next_target in zip(self.targets, self.targets[1:]):
                yield '{}: {}'.format(self._get_filename(target),
                                      self._get_filename(next_target))

        yield '{}: {}'.format(self._get_filename(self.targets[-1]),
                              ' '.join(self._get_filename(dep) for dep
                                       in self.dependencies))

        for command in self.commands:
            yield from self._pretty_print_command(command)

    @classmethod
    def _pretty_print_command(cls, command):
        tokens = iter(command)

        executable = cls._format_token(next(tokens))
        param_and_values, next_token = cls._consume_parameter_and_values(
            tokens)

        if param_and_values:
            indentation = ' ' * len(executable)
        elif next_token:
            action = next_token
            param_and_values, next_token = cls._consume_parameter_and_values(
                tokens)
            param_and_values.insert(0, action)
            indentation = ' ' * (len(executable) + 1 + len(action))

        yield '\t{} {}{}'.format(executable, ' '.join(
            cls._format_token(token) for token in param_and_values),
            ' \\' if next_token else '')

        while next_token:
            param_and_values, next_token = cls._consume_parameter_and_values(
                tokens, parameter=next_token)
            yield '\t{} {}{}'.format(indentation, ' '.join(
                cls._format_token(token) for token in param_and_values),
                ' \\' if next_token else '')

    @staticmethod
    def _consume_parameter_and_values(tokens, parameter=None):
        values = []

        token = None
        for token in tokens:
            if isinstance(token, str) and token.startswith('-'):
                if parameter is None:  # rename to "argument"?
                    parameter = token
                    token = None
                else:
                    break  # the next parameter encountered
            else:
                if parameter is None:
                    break
                else:
                    values.append(token)
                    token = None

        return ([parameter] if parameter else []) + values, token

    # TODO: asi sloučit s tím dole (budu potřebovat speciální zacházení
    #       s ShellPath, protože právě tak dávám do command programy)
    @staticmethod
    def _get_filename(obj):
        if hasattr(obj, 'path'):
            return obj.path.name
        elif hasattr(obj, 'name'):
            return obj.name
        else:
            return str(obj)

    # TODO: tohle vypadá trochu jako duplikát toho nahoře (_get_filename)
    @staticmethod
    def _format_token(token):
        # NOTE: řídit se podle přípony u spustitelných souborů (*.py) moc nejde
        #       protože mám taky systémový cesty ("rft-annotate") – no, prostě
        #       bude lepší, když se read_args (né, prostě tahle funkce, přece?)
        #       koukne na to, jestli je „cesta“ spustitelná, to je nejjednoduš-
        #       ší (a protože mám všechny programy linkovaný do pracovního
        #       adresáře, stačí „binárkám“ dávat ./ a zbytku souborů nic)
        # NOTE: samozřejmě většinou ty soubory nebudou ani existovat…
        if isinstance(token, ShellPath):
            return str(token)
        elif hasattr(token, 'path'):
            return token.path.name  # str(token.path)?
        elif isinstance(token, str):
            return token
        else:
            raise ValueError(token)
