"""Tests for sub-document region projection on hybrid source files (.razor, .vue)."""

from __future__ import annotations

from gdss.core.ast_parser import ASTParser
from gdss.core.region_projector import RegionProjector
from gdss.core.transform_types import SymbolType


def test_region_projector_can_project():
    assert RegionProjector.can_project("Components/Counter.razor") is True
    assert RegionProjector.can_project("Pages/Index.cshtml") is True
    assert RegionProjector.can_project("App.vue") is True
    assert RegionProjector.can_project("Button.svelte") is True
    assert RegionProjector.can_project("Program.cs") is False
    assert RegionProjector.can_project("index.ts") is False


def test_project_razor_blazor_component():
    razor_content = """@page "/counter"

<h1>Counter</h1>
<p>Current count: @currentCount</p>

<button class="btn btn-primary" @onclick="IncrementCount">Click me</button>

@code {
    private int currentCount = 0;

    private void IncrementCount()
    {
        currentCount++;
    }

    public void Reset()
    {
        currentCount = 0;
    }
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("Counter.razor", content=razor_content)

    by_name = {s.name: s for s in symbols}

    assert "IncrementCount" in by_name
    inc_sym = by_name["IncrementCount"]
    assert inc_sym.type == SymbolType.FUNCTION
    # In razor_content, IncrementCount starts around line 12
    assert inc_sym.start_line >= 11
    assert inc_sym.chart_location == "Counter.razor"
    assert inc_sym.language == "c_sharp"

    assert "Reset" in by_name
    reset_sym = by_name["Reset"]
    assert reset_sym.type == SymbolType.FUNCTION
    assert reset_sym.start_line > inc_sym.start_line


def test_project_vue_sfc_component():
    vue_content = """<template>
  <div class="user-card">
    <h2>{{ user.name }}</h2>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'UserCard',
  methods: {
    formatName(name: string): string {
      return name.toUpperCase();
    }
  }
});

function calculateScore(raw: number): number {
  return raw * 10;
}
</script>

<style scoped>
.user-card { color: red; }
</style>
"""
    parser = ASTParser()
    symbols = parser.parse_file("UserCard.vue", content=vue_content)

    by_name = {s.name: s for s in symbols}

    assert "calculateScore" in by_name
    score_sym = by_name["calculateScore"]
    assert score_sym.type == SymbolType.FUNCTION
    # In vue_content, calculateScore is after <script lang="ts"> (around line 18)
    assert score_sym.start_line >= 15
    assert score_sym.chart_location == "UserCard.vue"
    assert score_sym.language == "typescript"

