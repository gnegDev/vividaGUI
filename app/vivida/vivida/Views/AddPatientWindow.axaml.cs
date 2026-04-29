using System;
using Avalonia.Controls;
using vivida.ViewModels;

namespace vivida.Views;

public partial class AddPatientWindow : Window
{
    public AddPatientWindow()
    {
        InitializeComponent();
    }

    protected override void OnDataContextChanged(EventArgs e)
    {
        base.OnDataContextChanged(e);
        if (DataContext is AddPatientViewModel vm)
            vm.RequestClose += Close;
    }

    protected override void OnClosed(EventArgs e)
    {
        if (DataContext is AddPatientViewModel vm)
            vm.RequestClose -= Close;
        base.OnClosed(e);
    }
}
