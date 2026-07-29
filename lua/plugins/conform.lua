local prettier_filetypes = {
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact",
    "vue",
    "json",
    "jsonc",
    "json5",
    "yaml",
    "yaml.docker-compose",
    "markdown",
}

local formatters_by_ft = {
    lua = { "stylua" },
    rust = { "rustfmt", lsp_format = "fallback" },
    go = { "gofmt", lsp_format = "fallback" },
    bash = { "shfmt", lsp_format = "fallback" },
    sh = { "shfmt", lsp_format = "fallback" },
    java = { lsp_format = "fallback" },
}

for _, filetype in ipairs(prettier_filetypes) do
    formatters_by_ft[filetype] = {
        "prettierd",
        "prettier",
        stop_after_first = true,
        lsp_format = "fallback",
    }
end

require("conform").setup({
    formatters_by_ft = formatters_by_ft,
    default_format_opts = {
        timeout_ms = 3000,
        async = false,
        quiet = false,
        lsp_format = "fallback",
    },
    notify_no_formatters = false,
})
