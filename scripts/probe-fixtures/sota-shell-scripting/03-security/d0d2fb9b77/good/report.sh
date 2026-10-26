#!/usr/bin/env bash
awk -v col="$col" '{print $col}' data.tsv
