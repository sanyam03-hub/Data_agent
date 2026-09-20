import os
import requests
import pandas as pd

class ETLTools:

    def __init__(self):
        pass

    def extract_load(self, url: str, output_folder: str, format: str):
        """
        This tool ectracts the data from the API (url) and loads it into the desired location (output_folder)

        Args:
            url (str): The API endpoint from which to extract data.
            output_folder (str): The location where the extracted data will be loaded.
            format (str): The format in which to save the extracted data ('csv', 'json', or 'parquet').

        Returns:
            str: A message indicating the success or failure of the operation.

        """

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        output_folder = os.path.join(project_root, output_folder)

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            data = response.json()

            filename = os.path.join(output_folder, f"extracted_data.{format}")
            os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist

            df = pd.json_normalize(data['results'])  # Normalize the JSON data into a flat table
            if format == "csv":
                df.to_csv(filename, index=False)
            elif format == "json":
                df.to_json(filename, orient='records', lines=True)
            elif format == "parquet":
                df.to_parquet(filename, index=False)
            else:
                return f"Unsupported format: {format}"

            return f"Data extracted and loaded successfully to {filename}"
        except requests.RequestException as e:
            return f"Error during data extraction: {e}"
        except Exception as e:
            return f"Error during data loading: {e}"


    def transform_load_context(self, file_path:str):
        """
        Read the given file and return a small preview (top 3 rows).

        Args:
            file_path (str): Path to the data file (csv, json, parquet).

        Returns:
            str: String representation of the top 3 rows or an error message.
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        # Check file existence and provide a helpful message if missing
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format: {file_extension}"

        top_3_rows = str(df.head(3))
        return top_3_rows

    def execute_code(self, code: str, output_folder: str = None):
        """
        Execute the provided Python code string in a controlled namespace.

        After execution, any pandas DataFrame objects found in the namespace
        will be written to CSV files inside `output_folder` (if provided).

        Args:
            code (str): Code to execute.
            output_folder (str, optional): Directory to write discovered DataFrames.

        Returns:
            str: Success message including saved filenames, or an error message.
        """
        try:
            # prepare namespace with pandas imported
            ns = {}
            import pandas as _pd
            ns['pd'] = _pd

            exec(code, ns)

            saved = []
            if output_folder:
                os.makedirs(output_folder, exist_ok=True)
                for name, val in ns.items():
                    try:
                        if isinstance(val, _pd.DataFrame):
                            filename = os.path.join(output_folder, f"{name}.csv")
                            val.to_csv(filename, index=False)
                            saved.append(filename)
                    except Exception:
                        continue

            if saved:
                return f"Code executed successfully. Saved: {saved}"
            else:
                return "Code executed successfully. No DataFrame objects were found to save."
        except Exception as e:
            return f"Failed to execute code: {e}"


if __name__ == "__main__":
    obj = ETLTools()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(project_root, 'data', 'extract', 'extracted_data.csv')
    print(obj.transform_load_context(path))
