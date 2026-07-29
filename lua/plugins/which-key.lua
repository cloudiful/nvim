local wk = require("which-key")

wk.setup({
    preset = "modern",
    delay = 200,
})

wk.add({
    { "<leader>f", group = "find" },
    { "<leader>b", group = "buffers" },
    { "<leader>r", group = "rename" },
    { "<leader>c", group = "code" },
    { "<leader>j", group = "java" },
    { "<leader>w", proxy = "<c-w>", group = "windows" },
    { "[", group = "previous" },
    { "]", group = "next" },
})
