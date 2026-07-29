local M = {}

local function source(repo)
  return "https://github.com/" .. repo .. ".git"
end

local function plugin(repo, name, version)
  local spec = {
    src = source(repo),
    name = name,
  }
  if version ~= nil then
    spec.version = version
  end
  return spec
end

M.groups = {
  colorscheme = {
    plugin("catppuccin/nvim", "catppuccin"),
  },
  completion = {
    plugin("Saghen/blink.cmp", "blink.cmp", vim.version.range("1")),
    plugin("rafamadriz/friendly-snippets", "friendly-snippets"),
  },
  lsp = {
    plugin("neovim/nvim-lspconfig", "nvim-lspconfig"),
  },
  ui = {
    plugin("nvim-tree/nvim-web-devicons", "nvim-web-devicons"),
    plugin("akinsho/bufferline.nvim", "bufferline"),
    plugin("nvim-lualine/lualine.nvim", "lualine"),
  },
  conform = {
    plugin("stevearc/conform.nvim", "conform"),
  },
  fzf = {
    plugin("ibhagwan/fzf-lua", "fzf-lua"),
  },
  neo_tree = {
    plugin("nvim-lua/plenary.nvim", "plenary"),
    plugin("MunifTanjim/nui.nvim", "nui"),
    plugin("nvim-neo-tree/neo-tree.nvim", "neo-tree"),
  },
  diffview = {
    plugin("nvim-lua/plenary.nvim", "plenary"),
    plugin("sindrets/diffview.nvim", "diffview"),
  },
  noice = {
    plugin("MunifTanjim/nui.nvim", "nui"),
    plugin("folke/noice.nvim", "noice"),
  },
  gitsigns = {
    plugin("lewis6991/gitsigns.nvim", "gitsigns"),
  },
  which_key = {
    plugin("folke/which-key.nvim", "which-key"),
  },
  render_markdown = {
    plugin("MeanderingProgrammer/render-markdown.nvim", "render-markdown.nvim"),
  },
  java = {
    plugin("mfussenegger/nvim-jdtls", "nvim-jdtls"),
  },
}

M.configs = {
  colorscheme = "plugins.catppuccin",
  completion = "plugins.blink",
  lsp = "plugins.lsp",
  treesitter = "plugins.tree-sitter",
  ui = {
    "plugins.bufferline",
    "plugins.lualine",
  },
  conform = "plugins.conform",
  neo_tree = "plugins.neo-tree",
  noice = "plugins.noice",
  java = "plugins.java",
  which_key = "plugins.which-key",
}

M.startup_groups = {
  "colorscheme",
  "completion",
  "lsp",
  "ui",
}

M.startup_configs = {
  "colorscheme",
  "completion",
  "lsp",
  "treesitter",
  "ui",
}

M.diffview_commands = {
  "DiffviewOpen",
  "DiffviewClose",
  "DiffviewFileHistory",
  "DiffviewFocusFiles",
  "DiffviewToggleFiles",
  "DiffviewRefresh",
  "DiffviewLog",
}

function M.all()
  local result = {}
  local seen = {}

  for _, group in pairs(M.groups) do
    for _, spec in ipairs(group) do
      if not seen[spec.name] then
        result[#result + 1] = spec
        seen[spec.name] = true
      end
    end
  end

  table.sort(result, function(a, b)
    return a.name < b.name
  end)
  return result
end

return M
