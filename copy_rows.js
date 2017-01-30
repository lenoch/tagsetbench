function prepend_checkboxes()
{
    var rows = document.getElementsByTagName('tr');
    for (var row of rows) {
        row.innerHTML = '<td><input type="checkbox"></td>' + row.innerHTML;
    }
}

// https://developer.mozilla.org/en-US/docs/Web/Events/copy

function add_copy_listener()
{
    document.addEventListener('copy', copy_selected_rows);
}

function copy_selected_rows(event)
{
    var rows = document.getElementsByTagName('tr');
    var lines = [];

    for (var row of rows) {
        var checkbox = row.cells[0].children[0];
        if (checkbox.checked) {
            var cells_to_copy = [];
            for (var c = 1; c < row.cells.length; c++)
                cells_to_copy.push(row.cells[c].outerHTML);
            lines.push('<tr>' + cells_to_copy.join('') + '</tr>');
        }
    }

    if (lines.length) {
        table_html = '<table>\n' + lines.join('\n') + '\n</table>\n';
        // table_html = table_html.replace(' class="highest"', '')

        event.clipboardData.setData('text/plain', table_html);
        event.clipboardData.setData('text/html', table_html);

        event.preventDefault();
    }
}
