namespace vivida.ViewModels;

public class TabViewModel
{
    public string Header { get; }
    public string Content { get; }
    public TabViewModel(string header, string content)
    {
        Header = header;
        Content = content;
    }
}