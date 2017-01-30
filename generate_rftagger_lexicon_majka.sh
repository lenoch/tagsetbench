#!/bin/sh
PATH=/nlp/projekty/ajka/bin:$PATH
MAJKA_DB=/nlp/projekty/ajka/lib/majka.w-lt
RFTAGGER_LEXICON=rftagger-external-lexicon-majka.vert

cd /home/xsvobo15/tagsetbench/
/usr/bin/time -v ./majka.py --dictionary $MAJKA_DB --rftagger-lexicon $RFTAGGER_LEXICON
# zatím to frčí 4 minuty a momentálně to nespíš přeskakuje prefixy/sufixy (poslední je Zýkovém/Zýkův)
# na 12. minutě už to zase zapisuje, teď to je přes 100 mega
