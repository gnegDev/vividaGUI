using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using vivida.Models;

namespace vivida.ViewModels;

public partial class AddPatientViewModel : ObservableValidator
{
    // Обязательные поля

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [Required(ErrorMessage = "Обязательное поле")]
    [MinLength(1, ErrorMessage = "Обязательное поле")]
    private string _name = "";

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [CustomValidation(typeof(AddPatientViewModel), nameof(ValidateAge))]
    private decimal? _age;

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [CustomValidation(typeof(AddPatientViewModel), nameof(ValidateTumorSize))]
    private decimal? _tumorSize;

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [CustomValidation(typeof(AddPatientViewModel), nameof(ValidateKps))]
    private decimal? _kps;

    [ObservableProperty]
    private int _treatmentIndex;

    // Дозировки
    [ObservableProperty] private decimal? _doseMgPerM2;
    [ObservableProperty] private decimal? _cycles;
    [ObservableProperty] private decimal? _totalDoseGy;
    [ObservableProperty] private decimal? _fractions;

    // Генетические маркеры
    [ObservableProperty] private bool _mgmtMethylation;
    [ObservableProperty] private bool _idhMutation;
    [ObservableProperty] private bool _egfrAmplification;
    [ObservableProperty] private bool _tertMutation;
    [ObservableProperty] private bool _atrxMutation;

    // Клинические признаки
    [ObservableProperty] private decimal? _edemaVolume;
    [ObservableProperty] private decimal? _steroidDose;
    [ObservableProperty] private bool _antiseizureMeds;

    // Неврологические симптомы
    [ObservableProperty] private bool _hasHeadache;
    [ObservableProperty] private bool _hasSeizures;
    [ObservableProperty] private bool _hasMotorDeficit;
    [ObservableProperty] private bool _hasSensoryDeficit;
    [ObservableProperty] private bool _hasCognitiveDecline;
    [ObservableProperty] private bool _hasSpeechDisturbance;
    [ObservableProperty] private bool _hasVisualDisturbance;

    // Прочее
    [ObservableProperty] private int _genderIndex;
    [ObservableProperty] private int _resectionIndex;
    [ObservableProperty] private string _tumorLocation = "";
    [ObservableProperty] private bool _contrastEnhancement;
    [ObservableProperty] private string _stage = "";
    [ObservableProperty] private int _lateralizationIndex;
    [ObservableProperty] private string _ranoResponse = "";
    [ObservableProperty] private bool _familyHistory;
    [ObservableProperty] private bool _previousRadiation;

    public IEnumerable<string> TreatmentOptions { get; } = ["Химиолучевая терапия", "Химиотерапия", "Лучевая терапия"];
    public IEnumerable<string> GenderOptions { get; } = ["Не указан", "Мужской", "Женский"];
    public IEnumerable<string> ResectionOptions { get; } = ["Не указана", "Тотальная", "Субтотальная", "Биопсия"];
    public IEnumerable<string> LateralizationOptions { get; } = ["Не указана", "Левая", "Правая", "Билатеральная"];

    public bool Saved { get; private set; }
    public Patient? Result { get; private set; }

    public event Action? RequestClose;

    [RelayCommand]
    private void Save()
    {
        ValidateAllProperties();
        if (HasErrors) return;

        string[] treatments = ["chemoradiotherapy", "chemotherapy", "radiation"];
        string?[] genders = [null, "M", "F"];
        string?[] resections = [null, "total", "subtotal", "biopsy"];
        string?[] lateralizations = [null, "left", "right", "biliteral"];

        Result = new Patient
        {
            Name = Name.Trim(),
            PatientId = "",
            Age = (double)Age!.Value,
            TumorSizeBefore = (double)TumorSize!.Value,
            Kps = (double)Kps!.Value,
            Treatment = treatments[TreatmentIndex],
            DoseMgPerM2 = DoseMgPerM2.HasValue ? (double)DoseMgPerM2.Value : null,
            Cycles = Cycles.HasValue ? (int)Cycles.Value : null,
            TotalDoseGy = TotalDoseGy.HasValue ? (double)TotalDoseGy.Value : null,
            Fractions = Fractions.HasValue ? (int)Fractions.Value : null,
            MgmtMethylation = MgmtMethylation,
            IdhMutation = IdhMutation,
            EgfrAmplification = EgfrAmplification,
            TertMutation = TertMutation,
            AtrxMutation = AtrxMutation,
            EdemaVolume = EdemaVolume.HasValue ? (double)EdemaVolume.Value : null,
            SteroidDose = SteroidDose.HasValue ? (double)SteroidDose.Value : null,
            AntiseizureMeds = AntiseizureMeds,
            HasHeadache = HasHeadache,
            HasSeizures = HasSeizures,
            HasMotorDeficit = HasMotorDeficit,
            HasSensoryDeficit = HasSensoryDeficit,
            HasCognitiveDecline = HasCognitiveDecline,
            HasSpeechDisturbance = HasSpeechDisturbance,
            HasVisualDisturbance = HasVisualDisturbance,
            Gender = genders[GenderIndex],
            ResectionExtent = resections[ResectionIndex],
            TumorLocation = NullIfEmpty(TumorLocation),
            ContrastEnhancement = ContrastEnhancement,
            Stage = NullIfEmpty(Stage),
            Lateralization = lateralizations[LateralizationIndex],
            RanoResponse = NullIfEmpty(RanoResponse),
            FamilyHistory = FamilyHistory,
            PreviousRadiation = PreviousRadiation,
        };

        Saved = true;
        RequestClose?.Invoke();
    }

    [RelayCommand]
    private void Cancel() => RequestClose?.Invoke();

    // Валидаторы

    public static ValidationResult? ValidateAge(decimal? value, ValidationContext ctx)
    {
        if (value is null) return new ValidationResult("Обязательное поле");
        if (value < 0 || value > 120) return new ValidationResult("Возраст: 0–120");
        return ValidationResult.Success;
    }

    public static ValidationResult? ValidateTumorSize(decimal? value, ValidationContext ctx)
    {
        if (value is null) return new ValidationResult("Обязательное поле");
        if (value <= 0) return new ValidationResult("Должно быть больше 0");
        return ValidationResult.Success;
    }

    public static ValidationResult? ValidateKps(decimal? value, ValidationContext ctx)
    {
        if (value is null) return new ValidationResult("Обязательное поле");
        if (value < 0 || value > 100) return new ValidationResult("KPS: 0–100");
        return ValidationResult.Success;
    }

    private static string? NullIfEmpty(string s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
