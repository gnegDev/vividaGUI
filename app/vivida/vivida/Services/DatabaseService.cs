using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using vivida.Data;
using vivida.Models;

namespace vivida.Services;

public class DatabaseService
{
    private readonly AppDbContext _db;

    public DatabaseService(AppDbContext db) => _db = db;

    public async Task<List<Patient>> GetAllPatientsAsync() =>
        await _db.Patients.OrderByDescending(p => p.CreatedAt).ToListAsync();

    public async Task<Patient> AddPatientAsync(Patient patient)
    {
        patient.CreatedAt = DateTime.UtcNow;
        patient.PatientId = "PAT-" + Guid.NewGuid().ToString("N")[..8].ToUpper();
        _db.Patients.Add(patient);
        await _db.SaveChangesAsync();
        return patient;
    }

    public async Task DeletePatientAsync(int patientId)
    {
        var analyses = await _db.AnalysisResults
            .Where(a => a.PatientDbId == patientId).ToListAsync();
        _db.AnalysisResults.RemoveRange(analyses);

        var patient = await _db.Patients.FindAsync(patientId);
        if (patient is not null)
            _db.Patients.Remove(patient);

        await _db.SaveChangesAsync();
    }

    public async Task<AnalysisResult?> GetLatestAnalysisAsync(int patientDbId) =>
        await _db.AnalysisResults
            .Where(a => a.PatientDbId == patientDbId)
            .OrderByDescending(a => a.CreatedAt)
            .FirstOrDefaultAsync();

    public async Task<AnalysisResult> SaveAnalysisAsync(int patientDbId, string resultJson)
    {
        var result = new AnalysisResult
        {
            PatientDbId = patientDbId,
            CreatedAt = DateTime.UtcNow,
            ResultJson = resultJson
        };
        _db.AnalysisResults.Add(result);
        await _db.SaveChangesAsync();
        return result;
    }
}
