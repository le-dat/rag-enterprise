import pandas as pd
from pathlib import Path

def create_sample_excel():
    data = {
        "Product": ["Cloud Server Enterprise", "Database Cluster Pro", "API Gateway Standard", "VPN Tunnel Business"],
        "Base Price": ["$5000/mo", "$3000/mo", "$1200/mo", "$400/mo"],
        "AE Discount Limit": ["10%", "12%", "15%", "20%"],
        "Required Approval Level": ["Director", "Manager", "AE Self-sign", "AE Self-sign"]
    }

    df = pd.DataFrame(data)
    
    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / "sales_data.xlsx"
    
    # Save using openpyxl engine
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Discount Authority", index=False)
        
    print(f"✅ Created sample excel sheet at: {file_path}")

if __name__ == "__main__":
    create_sample_excel()
