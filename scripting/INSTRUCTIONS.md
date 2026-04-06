Run the script from the repo's root dir:

```bash
python3 scripting/script.py scripting/tfplan-1.json
```

This writes the output file to:

```text
scripting/generated-tf/tfplan-1.tf
```

You can also choose your own output file:

```bash
python3 scripting/script.py scripting/tfplan-1.json scripting/generated-tf/custom.tf
```
