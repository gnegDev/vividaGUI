using System;
using System.Text.Json;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using vivida.Models;
using vivida.Services;

namespace vivida.ViewModels;

public partial class PatientTabViewModel : ViewModelBase
{
    private readonly DatabaseService _dbService;
    private readonly ApiService _apiService;
    private readonly PatientService _patientService;

    public Patient Patient { get; }
    public string Header => Patient.Name;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(DoctorTreatmentDisplay))]
    [NotifyPropertyChangedFor(nameof(DoctorPredictionDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalTreatmentDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalPredictionDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalImprovementDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalChemoDoseDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalRadioTotalDoseDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalRadioFractionsDisplay))]
    [NotifyPropertyChangedFor(nameof(GlobalRadioBedDisplay))]
    [NotifyPropertyChangedFor(nameof(LocalTreatmentDisplay))]
    [NotifyPropertyChangedFor(nameof(LocalPredictionDisplay))]
    [NotifyPropertyChangedFor(nameof(LocalImprovementDisplay))]
    [NotifyPropertyChangedFor(nameof(RecommendationDisplay))]
    private OptimizeSummaryResponse? _analysisResult;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(AnalysisDateDisplay))]
    private DateTime? _analysisDate;

    [ObservableProperty] private bool _isAnalyzing;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(AnalyzeButtonLabel))]
    private bool _hasAnalysis;

    public string AnalyzeButtonLabel => HasAnalysis ? "Повторить анализ" : "Анализировать план лечения";

    public event Action<PatientTabViewModel>? CloseRequested;
    public event Func<string, string, Task>? ShowError;

    public PatientTabViewModel(Patient patient, DatabaseService dbService, ApiService apiService, PatientService patientService)
    {
        Patient = patient;
        _dbService = dbService;
        _apiService = apiService;
        _patientService = patientService;
    }

    public async Task LoadExistingAnalysisAsync()
    {
        var stored = await _dbService.GetLatestAnalysisAsync(Patient.Id);
        if (stored is null) return;

        AnalysisDate = stored.CreatedAt.ToLocalTime();
        AnalysisResult = JsonSerializer.Deserialize<OptimizeSummaryResponse>(stored.ResultJson);
        HasAnalysis = true;
    }

    [RelayCommand(CanExecute = nameof(CanAnalyze))]
    private async Task AnalyzeAsync()
    {
        IsAnalyzing = true;
        AnalyzeCommand.NotifyCanExecuteChanged();
        try
        {
            var request = _patientService.BuildRequest(Patient);
            var (response, rawJson) = await _apiService.OptimizeSummaryAsync(request);
            await _dbService.SaveAnalysisAsync(Patient.Id, rawJson);
            AnalysisResult = response;
            AnalysisDate = DateTime.Now;
            HasAnalysis = true;
        }
        catch (Exception ex)
        {
            if (ShowError is not null)
                await ShowError("Ошибка анализа", $"Не удалось выполнить анализ:\n{ex.Message}");
        }
        finally
        {
            IsAnalyzing = false;
            AnalyzeCommand.NotifyCanExecuteChanged();
        }
    }

    private bool CanAnalyze() => !IsAnalyzing;

    [RelayCommand]
    private void Close() => CloseRequested?.Invoke(this);

    // --- Display properties for patient fields ---

    public string TreatmentDisplay => TranslateTreatment(Patient.Treatment);
    public string GenderDisplay => Patient.Gender switch { "male" => "Мужской", "female" => "Женский", _ => "—" };
    public string ResectionDisplay => Patient.ResectionExtent switch { "total" => "Тотальная", "subtotal" => "Субтотальная", "biopsy" => "Биопсия", _ => "—" };
    public string LateralizationDisplay => Patient.Lateralization switch { "left" => "Левая", "right" => "Правая", _ => "—" };
    public string CreatedAtDisplay => Patient.CreatedAt.ToLocalTime().ToString("dd.MM.yyyy HH:mm");

    // --- Display properties for analysis ---

    public string DoctorTreatmentDisplay => TranslateTreatment(AnalysisResult?.DoctorPlan?.TreatmentType);
    public string DoctorPredictionDisplay => AnalysisResult?.DoctorPlan?.Prediction.ToString("F2") ?? "—";
    public string GlobalTreatmentDisplay => TranslateTreatment(AnalysisResult?.GlobalOptimal?.TreatmentType);
    public string GlobalPredictionDisplay => AnalysisResult?.GlobalOptimal?.Prediction.ToString("F2") ?? "—";
    public string GlobalImprovementDisplay => AnalysisResult?.GlobalOptimal?.ImprovementPercent.ToString("F1") ?? "—";
    public string GlobalChemoDoseDisplay => AnalysisResult?.GlobalOptimal?.Chemotherapy?.DoseMgPerM2?.ToString("F0") ?? "—";
    public string GlobalRadioTotalDoseDisplay => AnalysisResult?.GlobalOptimal?.Radiotherapy?.TotalDoseGy?.ToString("F0") ?? "—";
    public string GlobalRadioFractionsDisplay => AnalysisResult?.GlobalOptimal?.Radiotherapy?.Fractions?.ToString() ?? "—";
    public string GlobalRadioBedDisplay => AnalysisResult?.GlobalOptimal?.Radiotherapy?.Bed?.ToString("F1") ?? "—";
    public string LocalTreatmentDisplay => TranslateTreatment(AnalysisResult?.LocalOptimal?.TreatmentType);
    public string LocalPredictionDisplay => AnalysisResult?.LocalOptimal?.Prediction.ToString("F2") ?? "—";
    public string LocalImprovementDisplay => AnalysisResult?.LocalOptimal?.ImprovementPercent.ToString("F1") ?? "—";
    public string RecommendationDisplay => AnalysisResult?.Recommendation switch
    {
        "optimal" => "Оптимально",
        "minor_change" => "Незначительное изменение",
        "major_change" => "Значительное изменение",
        _ => "—"
    };
    public string AnalysisDateDisplay => AnalysisDate?.ToString("dd.MM.yyyy HH:mm") ?? "";

    private static string TranslateTreatment(string? t) => t switch
    {
        "chemoradiotherapy" => "Химиолучевая терапия",
        "chemotherapy" => "Химиотерапия",
        "radiation" => "Лучевая терапия",
        null or "" => "—",
        _ => t
    };
}
