require("bufferline").setup({
    options = {
        numbers = 'ordinal',
        offsets = {
            {
                filetype = "neo-tree",
                text = "Neo-tree",
                highlight = "Directory",
                text_align = "left",
            },
            {
                filetype = "snacks_layout_box",
            },
        },
    }
})

