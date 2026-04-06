import { createBackendModule } from '@backstage/backend-plugin-api';
import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node/alpha';
import { promises as fs } from 'fs';
import path from 'path';

const createMyCustomAction = () =>
  createTemplateAction({
    id: 'my:custom:action',
    description: 'Creates a file in the scaffolder workspace',
    schema: {
      input: {
        type: 'object',
        properties: {
          filename: {
            type: 'string',
            description: 'Name of the file to create in the workspace',
          },
          contents: {
            type: 'string',
            description: 'Text to write into the file',
          },
        },
      },
    },
    async handler(ctx) {
      const filename = ctx.input.filename ?? 'generated-file.txt';
      const contents = ctx.input.contents ?? 'Created by my:custom:action';
      const filePath = path.join(ctx.workspacePath, filename);

      await fs.writeFile(filePath, contents, 'utf8');
      ctx.logger.info(`Created ${filePath}`);
    },
  });

export default createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'custom-action',
  register(env) {
    env.registerInit({
      deps: {
        scaffolder: scaffolderActionsExtensionPoint,
      },
      async init({ scaffolder }) {
        scaffolder.addActions(createMyCustomAction());
      },
    });
  },
});
