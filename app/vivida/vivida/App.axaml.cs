using System.Linq;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Data.Core.Plugins;
using Avalonia.Markup.Xaml;
using Microsoft.EntityFrameworkCore;
using vivida.Data;
using vivida.Services;
using vivida.ViewModels;
using vivida.Views;

namespace vivida;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            DisableAvaloniaDataAnnotationValidation();

            var options = new DbContextOptionsBuilder<AppDbContext>()
                .UseSqlite("Data Source=vivida.db")
                .Options;

            var dbContext = new AppDbContext(options);
            dbContext.Database.EnsureCreated();

            var dbService = new DatabaseService(dbContext);
            var apiService = new ApiService();
            var patientService = new PatientService();

            var vm = new MainWindowViewModel(dbService, apiService, patientService);

            desktop.MainWindow = new MainWindow { DataContext = vm };
        }

        base.OnFrameworkInitializationCompleted();
    }

    private void DisableAvaloniaDataAnnotationValidation()
    {
        var toRemove = BindingPlugins.DataValidators
            .OfType<DataAnnotationsValidationPlugin>().ToArray();
        foreach (var plugin in toRemove)
            BindingPlugins.DataValidators.Remove(plugin);
    }
}
