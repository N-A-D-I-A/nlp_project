# nlp_project
To train the model, run the following command:
python main.py --train --cuda --model_name lstm/cnn --save_path model_name.pt 

To test the model, run the following command:
python main.py --test --cuda --model_name lstm/cnn --snapshot model_name.pt
