using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Input;
using vivida.Models;
using vivida.ViewModels;

namespace vivida.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    protected override async void OnOpened(System.EventArgs e)
    {
        base.OnOpened(e);

        if (DataContext is not MainWindowViewModel vm) return;

        vm.ShowAddPatientDialog += ShowAddPatientDialogAsync;
        vm.ShowMessageDialog += ShowMessageDialogAsync;
        vm.ShowConfirmDialog += ShowConfirmDialogAsync;

        PatientListBox.DoubleTapped += async (_, _) =>
        {
            if (PatientListBox.SelectedItem is Patient p)
                await vm.OpenPatientCommand.ExecuteAsync(p);
        };

        await vm.InitializeAsync();
    }

    private async Task<Patient?> ShowAddPatientDialogAsync()
    {
        var addVm = new AddPatientViewModel();
        var win = new AddPatientWindow { DataContext = addVm };
        await win.ShowDialog(this);
        return addVm.Saved ? addVm.Result : null;
    }

    private async Task ShowMessageDialogAsync(string title, string message)
    {
        var dlg = new MessageDialog(title, message);
        await dlg.ShowDialog(this);
    }

    private async Task<bool> ShowConfirmDialogAsync(string title, string message)
    {
        var dlg = new ConfirmDialog(title, message);
        await dlg.ShowDialog(this);
        return dlg.Confirmed;
    }
}
