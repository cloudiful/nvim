require("neo-tree").setup({
    close_if_last_window = true,
    filesystem = {
        follow_current_file = {
            enabled = true,
            leave_dirs_open = false,
        },
        window = {
            mappings = {
                ["/"] = "fuzzy_finder",
                ["H"] = "toggle_hidden",
                ["<bs>"] = "navigate_up",
                ["."] = "set_root",
                ["P"] = {
                    "toggle_preview",
                    config = {
                        use_float = false,
                    },
                },
            },
        },
    },
})
