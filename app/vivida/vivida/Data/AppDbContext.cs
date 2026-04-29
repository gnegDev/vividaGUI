using Microsoft.EntityFrameworkCore;
using vivida.Models;

namespace vivida.Data;

public class AppDbContext : DbContext
{
    public DbSet<Patient> Patients { get; set; }
    public DbSet<AnalysisResult> AnalysisResults { get; set; }

    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AnalysisResult>()
            .HasOne(a => a.Patient)
            .WithMany()
            .HasForeignKey(a => a.PatientDbId);
    }
}
