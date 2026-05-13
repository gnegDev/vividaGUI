using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using vivida.Models;
using vivida.Services;

namespace vivida.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly DatabaseService _dbService;
    private readonly ApiService _apiService;
    private readonly PatientService _patientService;

    private List<Patient> _allPatients = new();

    [ObservableProperty] private string _searchText = "";
    [ObservableProperty] private ObservableCollection<Patient> _filteredPatients = new();
    [ObservableProperty] private ObservableCollection<PatientTabViewModel> _tabs = new();
    [ObservableProperty] private PatientTabViewModel? _selectedTab;

    public event Func<Task<Patient?>>? ShowAddPatientDialog;
    public event Func<string, string, Task>? ShowMessageDialog;
    public event Func<string, string, Task<bool>>? ShowConfirmDialog;

    public MainWindowViewModel(DatabaseService dbService, ApiService apiService, PatientService patientService)
    {
        _dbService = dbService;
        _apiService = apiService;
        _patientService = patientService;
    }

    public async Task InitializeAsync()
    {
        _allPatients = await _dbService.GetAllPatientsAsync();
        ApplyFilter();
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        var q = SearchText.Trim();
        var list = string.IsNullOrEmpty(q)
            ? _allPatients
            : _allPatients.Where(p => p.Name.Contains(q, StringComparison.OrdinalIgnoreCase)).ToList();
        FilteredPatients = new ObservableCollection<Patient>(list);
    }

    [RelayCommand]
    private async Task AddPatientAsync()
    {
        if (ShowAddPatientDialog is null) return;
        var patient = await ShowAddPatientDialog();
        if (patient is null) return;

        var saved = await _dbService.AddPatientAsync(patient);
        _allPatients.Insert(0, saved);
        
        ApplyFilter();
    }

    [RelayCommand]
    private async Task DeletePatientAsync(Patient patient)
    {
        if (ShowConfirmDialog is not null)
        {
            var confirmed = await ShowConfirmDialog(
                "Удаление пациента",
                $"Удалить пациента «{patient.Name}»?\nВсе результаты анализов будут также удалены.");
            if (!confirmed) return;
        }

        var tab = Tabs.FirstOrDefault(t => t.Patient.Id == patient.Id);
        if (tab is not null) Tabs.Remove(tab);

        await _dbService.DeletePatientAsync(patient.Id);
        _allPatients.Remove(patient);
        ApplyFilter();
    }

    [RelayCommand]
    private async Task OpenPatientAsync(Patient patient)
    {
        var existing = Tabs.FirstOrDefault(t => t.Patient.Id == patient.Id);
        if (existing is not null)
        {
            SelectedTab = existing;
            return;
        }

        var tab = new PatientTabViewModel(patient, _dbService, _apiService, _patientService);
        tab.CloseRequested += t => Tabs.Remove(t);
        tab.ShowError += async (title, msg) =>
        {
            if (ShowMessageDialog is not null)
                await ShowMessageDialog(title, msg);
        };

        await tab.LoadExistingAnalysisAsync();
        Tabs.Add(tab);
        SelectedTab = tab;
    }

    [RelayCommand]
    private void CloseTab(PatientTabViewModel tab) => Tabs.Remove(tab);

    [RelayCommand]
    private async Task CheckStatusAsync()
    {
        if (ShowMessageDialog is null) return;
        try
        {
            var result = await _apiService.GetHealthAsync();
            await ShowMessageDialog("Статус сервиса", $"Сервис работает\n\n{result}");
        }
        catch (Exception ex)
        {
            await ShowMessageDialog("Ошибка подключения", $"Сервис недоступен:\n{ex.Message}");
        }
    }

    [RelayCommand]
    private async Task ShowInfoAsync()
    {
        if (ShowMessageDialog is null) return;
        await ShowMessageDialog("О приложении",
            "Вивида — система анализа планов лечения глиобластомы.\n" +
            "Использует ML-модель для оптимизации лечения.\n\n" +
            "Вальтуилье И.А. 2026\n" +
            "Версия 1.0");
    }

    [RelayCommand]
    private static void Exit()
    {
        if (Avalonia.Application.Current?.ApplicationLifetime
            is Avalonia.Controls.ApplicationLifetimes.IClassicDesktopStyleApplicationLifetime lt)
            lt.Shutdown();
    }
}
