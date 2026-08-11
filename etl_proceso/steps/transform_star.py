# -*- coding: utf-8 -*-
"""Transform: truncate + rebuild dims/fact_ventas (wrapper de etl.transform_fact_dimensions)."""
from __future__ import annotations


def run() -> None:
    from etl.transform_fact_dimensions import main

    main()


if __name__ == "__main__":
    run()
