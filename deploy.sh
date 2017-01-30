#!/bin/sh
for spoustec in *.desktop;
    do ln -s $spoustec ~/.local/share/applications;
done;
