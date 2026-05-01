from __future__ import annotations

from apps.blog.management.commands.seed_data import Command as SeedDataCommand


class Command(SeedDataCommand):
    help = "Seed realistic local development data."
