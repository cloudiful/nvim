local ok, blink = pcall(require, "blink.cmp")
if not ok then
    return
end

blink.setup({
    keymap = {
        preset = "super-tab",
    },
    signature = { enabled = true },
    fuzzy = {
        implementation = "prefer_rust_with_warning",
        prebuilt_binaries = {
            download = false,
        },
    },
    appearance = {},
    sources = {
        default = { "lsp", "path", "buffer", "snippets" },
    },
    completion = {
        menu = { border = "rounded" },
        documentation = {
            auto_show = true,
            window = { border = "rounded" }
        },
    },
})
