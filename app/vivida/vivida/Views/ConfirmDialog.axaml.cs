using Avalonia.Controls;
using Avalonia.Interactivity;

namespace vivida.Views;

public partial class ConfirmDialog : Window
{
    public bool Confirmed { get; private set; }

    public ConfirmDialog() => InitializeComponent();

    public ConfirmDialog(string title, string message)
    {
        InitializeComponent();
        Title = title;
        MessageText.Text = message;
    }

    private void OnYesClick(object? sender, RoutedEventArgs e)
    {
        Confirmed = true;
        Close();
    }

    private void OnNoClick(object? sender, RoutedEventArgs e) => Close();
}
