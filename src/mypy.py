import subprocess
import os

if __name__ == "__main__":
    file_path = "src/colleso.py"
    repo_name = "examples"
    tests_dir = f"../uploads/{repo_name}"
    print(subprocess.run(['pwd'], cwd=tests_dir))
    # print(os.path.exists(f"{tests_dir}/tests"))
    # result = subprocess.run(["awk", "{print $0}"], input=subprocess.run(["pwd"], capture_output=True, text=True).stdout,
    #                         text=True, capture_output=True)
    # print(result.stdout.strip())
    # result = subprocess.run(["awk", f'$1 == "{file_path}" {{if (NF > 4) print $4, substr($0, index($0, $5)); else print $4, "NONE"}}', "coverage.log"], cwd=f"{tests_dir}/tests",
    #                capture_output=True, text=True).stdout
    # cov_score, missed_lines = result.split(maxsplit=1)
    # print(cov_score, missed_lines, sep='\n')
